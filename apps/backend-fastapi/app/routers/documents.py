import unicodedata
import uuid
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel

from app import database, minio_client
from app.services.ingestion import process_document

logger = logging.getLogger(__name__)
router = APIRouter()


def _fix_filename(name: str) -> str:
    """Corrige nombres de archivo con doble encoding Latin-1/UTF-8 (ej: ContrataciÃ³n → Contratación)."""
    try:
        fixed = name.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        fixed = name
    return unicodedata.normalize('NFC', fixed)


class ProcessRequest(BaseModel):
    document_id: str


class UploadDocumentRequest(BaseModel):
    name: str
    minio_path: str
    uploaded_by: int


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    uploaded_by: int = Form(...),
):
    """
    Recibe un PDF del frontend, lo sube a MinIO y registra el documento en DB.
    El cliente debe llamar a /process después para iniciar el pipeline de ingestión.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    filename = _fix_filename(file.filename)
    doc_id = str(uuid.uuid4())
    safe_name = filename.replace(" ", "_")
    minio_path = f"{doc_id}/{safe_name}"

    minio_client.upload_bytes(minio_path, pdf_bytes, content_type="application/pdf")

    with database.get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute(
            """INSERT INTO documents (id, name, minio_path, status, uploaded_by)
               VALUES (%s, %s, %s, 'PROCESSING', %s)""",
            (doc_id, filename, minio_path, uploaded_by),
        )
        conn.commit()

    logger.info(f"Documento subido: {doc_id} ({filename}) por usuario {uploaded_by}")
    return {"document_id": doc_id}


@router.post("/process")
def trigger_processing(req: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Recibe document_id y lanza el pipeline de ingestión en background.
    Llamado por NestJS después de subir el PDF a MinIO.
    """
    background_tasks.add_task(process_document, req.document_id)
    return {"message": "Procesamiento iniciado", "document_id": req.document_id}


@router.post("/register")
def register_document(req: UploadDocumentRequest):
    """
    Registra un nuevo documento en la DB con status PROCESSING.
    Usado por NestJS al recibir el upload del usuario.
    """
    doc_id = str(uuid.uuid4())
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute(
            """INSERT INTO documents (id, name, minio_path, status, uploaded_by)
               VALUES (%s, %s, %s, 'PROCESSING', %s)""",
            (doc_id, req.name, req.minio_path, req.uploaded_by),
        )
        conn.commit()
    return {"document_id": doc_id, "status": "PROCESSING"}


@router.get("/")
def list_documents():
    with database.get_cursor() as (cur, conn):
        cur.execute(
            "SELECT id, name, status, progress, created_at FROM documents ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/{document_id}")
def get_document(document_id: str):
    with database.get_cursor() as (cur, conn):
        cur.execute(
            "SELECT id, name, minio_path, status, progress, created_at FROM documents WHERE id = %s",
            (document_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return dict(row)


@router.delete("/{document_id}")
def delete_document(document_id: str):
    with database.get_cursor() as (cur, _):
        cur.execute("SELECT minio_path FROM documents WHERE id = %s", (document_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    minio_path = row["minio_path"]

    with database.get_cursor(dict_cursor=False) as (cur, conn):
        # Los chunks se eliminan en cascada por la FK ON DELETE CASCADE
        cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        conn.commit()

    try:
        minio_client.delete_object(minio_path)
    except Exception as e:
        logger.warning(f"No se pudo eliminar objeto de MinIO {minio_path}: {e}")

    return {"message": "Documento eliminado"}
