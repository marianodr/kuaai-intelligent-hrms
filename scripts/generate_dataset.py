#!/usr/bin/env python3
"""
Genera un dataset de evaluación RAG a partir de los chunks existentes en la DB.
Usa Groq para crear una pregunta y respuesta esperada por chunk.

Uso:
    python scripts/generate_dataset.py [--chunks-per-doc N] [--output scripts/dataset.json]

Variables de entorno (desde .env en la raíz del repo):
    POSTGRES_HOST (default: localhost), POSTGRES_PORT (default: 5432)
    POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    GROQ_API_KEY, GROQ_MODEL
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import psycopg2
import psycopg2.extras
from langchain_groq import ChatGroq

from dotenv import load_dotenv, dotenv_values as _dv

_env_file = Path(__file__).parent.parent / ".env"
load_dotenv(_env_file)                  # shell vars ganan (útil para POSTGRES_HOST=localhost)
_file = _dv(_env_file)                  # lectura directa del archivo para claves sensibles

POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB       = os.getenv("POSTGRES_DB", "kuaai")
POSTGRES_USER     = os.getenv("POSTGRES_USER", "kuaai_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "kuaai_password")
GROQ_API_KEY      = _file.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY", "")
GROQ_MODEL        = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")

PROMPT = """Dado el siguiente fragmento de un documento de RRHH empresarial, generá UNA pregunta concreta que un empleado podría hacerle al asistente de RRHH y que este fragmento responde total o parcialmente. Incluí también la respuesta esperada basada EXCLUSIVAMENTE en el fragmento.

Respondé ÚNICAMENTE con JSON válido en este formato, sin texto adicional:
{{"question": "...", "answer": "..."}}

Fragmento:
{content}"""


def get_conn():
    return psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, dbname=POSTGRES_DB,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def sample_chunks(conn, chunks_per_doc: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dc.id, dc.content, dc.chunk_index,
                   LENGTH(dc.content) AS char_count,
                   d.name AS document_name, d.id AS document_id
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'READY' AND LENGTH(dc.content) > 150
            ORDER BY dc.document_id, dc.chunk_index
        """)
        rows = [dict(r) for r in cur.fetchall()]

    by_doc: dict[str, list] = defaultdict(list)
    for r in rows:
        by_doc[r["document_id"]].append(r)

    sampled = []
    for doc_chunks in by_doc.values():
        step = max(1, len(doc_chunks) // chunks_per_doc)
        sampled.extend(doc_chunks[::step][:chunks_per_doc])

    return sampled


def _extract_json(text: str) -> dict | None:
    """Extrae el primer objeto JSON válido del texto, ignorando thinking tags y texto extra."""
    # Remover bloques <think>...</think> del modelo
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    start = text.find('{')
    if start == -1:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def generate_qa(llm: ChatGroq, chunk: dict) -> dict | None:
    prompt = PROMPT.format(content=chunk["content"][:1500])
    try:
        text = llm.invoke(prompt).content.strip()
        data = _extract_json(text)
        if not data or not data.get("question") or not data.get("answer"):
            print(f"    ⚠ No se pudo extraer JSON válido")
            return None
        return {
            "question":        data["question"],
            "ground_truth":    data["answer"],
            "source_document": chunk["document_name"],
            "source_chunk_id": chunk["id"],
            "source_content":  chunk["content"],
        }
    except Exception as e:
        print(f"    ⚠ Error: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks-per-doc", type=int, default=5,
                        help="Cantidad de chunks a samplear por documento (default: 5)")
    parser.add_argument("--output", default="scripts/dataset.json",
                        help="Archivo de salida (default: scripts/dataset.json)")
    args = parser.parse_args()

    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY no está configurado en .env")
        sys.exit(1)

    llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0)

    print(f"Conectando a {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}...")
    conn = get_conn()
    chunks = sample_chunks(conn, args.chunks_per_doc)
    conn.close()

    if not chunks:
        print("No se encontraron chunks. Verificá que haya documentos con status='READY'.")
        sys.exit(1)

    print(f"Chunks seleccionados: {len(chunks)} ({args.chunks_per_doc} por documento)")
    print(f"Generando preguntas con {GROQ_MODEL}...\n")

    dataset = []
    for i, chunk in enumerate(chunks):
        print(f"[{i+1}/{len(chunks)}] {chunk['document_name']} — chunk #{chunk['chunk_index']}")
        qa = generate_qa(llm, chunk)
        if qa:
            dataset.append(qa)
            print(f"  Q: {qa['question'][:90]}")

    output = Path(args.output)
    output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2))
    print(f"\n✓ Dataset: {len(dataset)} muestras → {output}")


if __name__ == "__main__":
    main()
