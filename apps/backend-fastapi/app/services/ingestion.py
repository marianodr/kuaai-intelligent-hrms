import tempfile
import os
import logging
from docling.document_converter import DocumentConverter
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app import database, minio_client, embeddings as emb_service

logger = logging.getLogger(__name__)

# 1000 chars con 10% overlap — recomendado por skill langchain-rag
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""],
)

_converter = DocumentConverter()


def process_document(document_id: str) -> None:
    """
    Pipeline completo: MinIO → Docling → chunks → embeddings → pgvector.
    Actualiza el status del documento en la DB al finalizar.
    """
    try:
        _set_document_status(document_id, "PROCESSING")

        minio_path = _get_minio_path(document_id)
        logger.info(f"Procesando documento {document_id} desde {minio_path}")

        pdf_bytes = minio_client.download_to_bytes(minio_path)
        text = _extract_text(pdf_bytes)
        logger.info(f"Texto extraído: {len(text)} caracteres")

        chunks = _splitter.split_text(text)
        logger.info(f"Chunks generados: {len(chunks)}")

        embeddings = emb_service.get_embeddings_batch(chunks)
        _store_chunks(document_id, chunks, embeddings)
        logger.info(f"Chunks almacenados en pgvector: {len(chunks)}")

        _set_document_status(document_id, "READY")

    except Exception as e:
        logger.error(f"Error procesando documento {document_id}: {e}")
        _set_document_status(document_id, "ERROR")
        raise


def _extract_text(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = _converter.convert(source=tmp_path)
        return result.document.export_to_markdown()
    finally:
        os.unlink(tmp_path)


def _get_minio_path(document_id: str) -> str:
    with database.get_cursor() as (cur, conn):
        cur.execute("SELECT minio_path FROM documents WHERE id = %s", (document_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Documento {document_id} no encontrado")
        return row["minio_path"]


def _store_chunks(document_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        # Eliminar chunks previos si el documento se reprocesa
        cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            emb_str = emb_service.embedding_to_pg_str(embedding)
            cur.execute(
                """INSERT INTO document_chunks (document_id, content, embedding, chunk_index)
                   VALUES (%s, %s, %s::vector, %s)""",
                (document_id, chunk, emb_str, idx),
            )
        conn.commit()


def _set_document_status(document_id: str, status: str) -> None:
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute(
            "UPDATE documents SET status = %s WHERE id = %s",
            (status, document_id),
        )
        conn.commit()
