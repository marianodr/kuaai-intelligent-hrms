import tempfile
import os
import time
import logging
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app import database, minio_client, embeddings as emb_service
from app.config import settings

logger = logging.getLogger(__name__)

# 1000 chars con 10% overlap — recomendado por skill langchain-rag
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _build_converter() -> DocumentConverter:
    if not settings.docling_ocr_enabled:
        return DocumentConverter()
    try:
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        opts = PdfPipelineOptions(do_ocr=True)
        logger.info("Docling: OCR activado")
        return DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )
    except ImportError:
        logger.warning("docling.datamodel.pipeline_options no disponible; OCR desactivado")
        return DocumentConverter()


_converter = _build_converter()


def process_document(document_id: str) -> None:
    """
    Pipeline completo: MinIO → Docling → chunks → embeddings → pgvector.
    Actualiza el status del documento en la DB al finalizar.
    """
    t0 = time.perf_counter()

    def elapsed() -> str:
        return f"{time.perf_counter() - t0:.1f}s"

    try:
        _set_status_and_progress(document_id, "PROCESSING", "Descargando PDF...")

        minio_path = _get_minio_path(document_id)
        logger.info(f"[{document_id}] Pipeline iniciado — minio_path={minio_path}")

        t1 = time.perf_counter()
        pdf_bytes = minio_client.download_to_bytes(minio_path)
        logger.info(
            f"[{document_id}] [1/4] PDF descargado — "
            f"{len(pdf_bytes):,} bytes ({time.perf_counter() - t1:.1f}s)"
        )

        t2 = time.perf_counter()
        _set_progress(document_id, "Extrayendo texto con Docling...")
        text = _extract_text(pdf_bytes)
        logger.info(
            f"[{document_id}] [2/4] Texto extraído por Docling — "
            f"{len(text):,} caracteres ({time.perf_counter() - t2:.1f}s)"
        )

        t3 = time.perf_counter()
        _set_progress(document_id, "Dividiendo en fragmentos...")
        chunks = _splitter.split_text(text)
        logger.info(
            f"[{document_id}] [3/4] Chunking completado — "
            f"{len(chunks)} chunks ({time.perf_counter() - t3:.1f}s)"
        )

        t4 = time.perf_counter()
        _set_progress(document_id, "Generando embeddings...")
        embeddings = emb_service.get_embeddings_batch(chunks)
        _store_chunks(document_id, chunks, embeddings)
        logger.info(
            f"[{document_id}] [4/4] Embeddings generados y almacenados en pgvector — "
            f"{len(chunks)} vectores ({time.perf_counter() - t4:.1f}s)"
        )

        _set_status_and_progress(document_id, "READY", None)
        logger.info(f"[{document_id}] Pipeline completado exitosamente — total {elapsed()}")

    except Exception as e:
        logger.error(
            f"[{document_id}] Pipeline fallido después de {elapsed()} — {e}",
            exc_info=True,
        )
        _set_status_and_progress(document_id, "ERROR", None)
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


def _set_status_and_progress(document_id: str, status: str, progress: str | None) -> None:
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute(
            "UPDATE documents SET status = %s, progress = %s WHERE id = %s",
            (status, progress, document_id),
        )
        conn.commit()


def _set_progress(document_id: str, progress: str) -> None:
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute(
            "UPDATE documents SET progress = %s WHERE id = %s",
            (progress, document_id),
        )
        conn.commit()
