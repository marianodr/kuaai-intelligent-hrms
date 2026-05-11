import uuid
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app import database, minio_client
from app.services.ingestion import process_document

logger = logging.getLogger(__name__)
router = APIRouter()


class ProcessRequest(BaseModel):
    document_id: str


class UploadDocumentRequest(BaseModel):
    name: str
    minio_path: str
    uploaded_by: int


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
            "SELECT id, name, status, created_at FROM documents ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/{document_id}")
def get_document(document_id: str):
    with database.get_cursor() as (cur, conn):
        cur.execute(
            "SELECT id, name, minio_path, status, created_at FROM documents WHERE id = %s",
            (document_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return dict(row)


@router.delete("/{document_id}")
def delete_document(document_id: str):
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        # Los chunks se eliminan en cascada por la FK ON DELETE CASCADE
        cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        conn.commit()
    return {"message": "Documento eliminado"}
