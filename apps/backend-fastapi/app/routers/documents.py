import math
import unicodedata
import uuid
import logging
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel

from app import database, minio_client, embeddings as emb_service
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


@router.get("/{document_id}/download")
def download_document(document_id: str):
    """Descarga el PDF del documento directamente desde MinIO (proxy para el frontend)."""
    with database.get_cursor() as (cur, conn):
        cur.execute(
            "SELECT minio_path, name FROM documents WHERE id = %s",
            (document_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    try:
        data, content_type = minio_client.get_bytes(row["minio_path"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al obtener archivo: {e}")

    # Content-Disposition debe ir en Latin-1: un fallback ASCII (sin tildes,
    # para clientes viejos) + filename* en UTF-8 percent-encoded (RFC 6266)
    # para que los navegadores modernos muestren el nombre real.
    ascii_fallback = (
        unicodedata.normalize("NFKD", row["name"])
        .encode("ascii", errors="ignore")
        .decode("ascii")
        .replace(" ", "_")
    ) or "documento.pdf"
    encoded_name = quote(row["name"])
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_name}'
            )
        },
    )


class ChunkSearchRequest(BaseModel):
    query: str
    document_id: str | None = None
    limit: int = 8


def _embedding_stats(embedding_text: str) -> dict:
    vals = [float(x) for x in embedding_text.strip("[]").split(",")]
    n = len(vals)
    norm = math.sqrt(sum(v * v for v in vals))
    max_v = max(vals)
    min_v = min(vals)
    sparsity = round(sum(1 for v in vals if abs(v) < 0.01) / n, 4)
    return {
        "dims": n,
        "norm": round(norm, 4),
        "max": round(max_v, 6),
        "min": round(min_v, 6),
        "sparsity": sparsity,
        "sample": [round(v, 6) for v in vals[:8]],
    }


@router.get("/{document_id}/chunks")
def get_document_chunks(document_id: str):
    """Devuelve todos los chunks de un documento con métricas de embedding. Solo admin."""
    with database.get_cursor() as (cur, conn):
        cur.execute("SELECT 1 FROM documents WHERE id = %s", (document_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        cur.execute(
            """SELECT id, chunk_index, content, created_at,
                      LENGTH(content) AS char_count,
                      embedding::text AS embedding_text
               FROM document_chunks
               WHERE document_id = %s
               ORDER BY chunk_index""",
            (document_id,),
        )
        rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
            "char_count": r["char_count"],
            "estimated_tokens": r["char_count"] // 4,
            "embedding": _embedding_stats(r["embedding_text"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("/chunks/search")
def search_chunks(req: ChunkSearchRequest):
    """Búsqueda semántica sobre chunks. Devuelve resultados ordenados por similitud."""
    embedding = emb_service.get_embedding(req.query)
    emb_str = emb_service.embedding_to_pg_str(embedding)

    with database.get_cursor() as (cur, conn):
        if req.document_id:
            cur.execute(
                """SELECT dc.id, dc.chunk_index, dc.content, dc.created_at,
                          d.id AS document_id, d.name AS document_name,
                          LENGTH(dc.content) AS char_count,
                          dc.embedding::text AS embedding_text,
                          ROUND((1 - (dc.embedding <=> %s::vector))::numeric, 4) AS similarity
                   FROM document_chunks dc
                   JOIN documents d ON dc.document_id = d.id
                   WHERE dc.document_id = %s AND d.status = 'READY'
                   ORDER BY dc.embedding <=> %s::vector
                   LIMIT %s""",
                (emb_str, req.document_id, emb_str, req.limit),
            )
        else:
            cur.execute(
                """SELECT dc.id, dc.chunk_index, dc.content, dc.created_at,
                          d.id AS document_id, d.name AS document_name,
                          LENGTH(dc.content) AS char_count,
                          dc.embedding::text AS embedding_text,
                          ROUND((1 - (dc.embedding <=> %s::vector))::numeric, 4) AS similarity
                   FROM document_chunks dc
                   JOIN documents d ON dc.document_id = d.id
                   WHERE d.status = 'READY'
                   ORDER BY dc.embedding <=> %s::vector
                   LIMIT %s""",
                (emb_str, emb_str, req.limit),
            )
        rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
            "char_count": r["char_count"],
            "estimated_tokens": r["char_count"] // 4,
            "document_id": str(r["document_id"]),
            "document_name": r["document_name"],
            "similarity": float(r["similarity"]),
            "embedding": _embedding_stats(r["embedding_text"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


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
