#!/usr/bin/env python3
"""
Evaluación del pipeline RAG con RAGAS 0.2.

Flujo:
  1. Carga el dataset generado por generate_dataset.py
  2. Para cada pregunta: recupera chunks (retrieval) y genera respuesta (generation)
  3. Evalúa con RAGAS: Faithfulness, Answer Relevancy, Context Precision, Context Recall
  4. Imprime resultados y guarda un JSON con scores por muestra

Uso:
    # Generar dataset primero:
    python scripts/generate_dataset.py [--chunks-per-doc 5]

    # Evaluar:
    python scripts/eval_rag.py [--dataset scripts/dataset.json] [--top-k 4]

    # Comparar configuraciones:
    EMBEDDINGS_MODEL=paraphrase-multilingual-mpnet-base-v2 python scripts/eval_rag.py --top-k 6

Variables de entorno (desde .env):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    GROQ_API_KEY, GROQ_MODEL
    EMBEDDINGS_MODEL (default: all-MiniLM-L6-v2)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
from langchain_core.embeddings import Embeddings
from langchain_groq import ChatGroq  # usado para la generación de respuestas RAG
from sentence_transformers import SentenceTransformer

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
EMBEDDINGS_MODEL  = os.getenv("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")

GENERATION_PROMPT = """Sos un asistente de RRHH. Respondé la pregunta basándote EXCLUSIVAMENTE en los fragmentos de documentos proporcionados. Si la información no está en los fragmentos, decilo claramente.

Contexto:
{context}

Pregunta: {question}

Respuesta:"""


# ── Embeddings wrapper compatible con LangChain/RAGAS ──────────────────────

class STEmbeddings(Embeddings):
    """SentenceTransformer wrapped como LangChain Embeddings."""

    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()


# ── DB helpers ──────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, dbname=POSTGRES_DB,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def retrieve(conn, st_model: SentenceTransformer, question: str, top_k: int) -> list[str]:
    emb = st_model.encode(question, normalize_embeddings=True).tolist()
    emb_str = "[" + ",".join(f"{x:.8f}" for x in emb) + "]"
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dc.content,
                   ROUND((1 - (dc.embedding <=> %s::vector))::numeric, 3) AS similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'READY'
            ORDER BY dc.embedding <=> %s::vector
            LIMIT %s
        """, (emb_str, emb_str, top_k))
        return [r["content"] for r in cur.fetchall()]


def generate(llm: ChatGroq, question: str, contexts: list[str]) -> str:
    ctx = "\n\n---\n\n".join(contexts) if contexts else "Sin contexto disponible."
    text = llm.invoke(GENERATION_PROMPT.format(context=ctx, question=question)).content
    # qwen3.6-27b incluye <think>...</think> — removemos antes de pasar a RAGAS
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    return text


# ── Evaluación ──────────────────────────────────────────────────────────────

def run(dataset_path: str, top_k: int) -> None:
    try:
        import instructor
        from groq import Groq
        from ragas import SingleTurnSample
        from ragas.llms import llm_factory
        from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings
        from ragas.metrics.collections import (
            AnswerRelevancy,
            Faithfulness,
            ContextPrecisionWithReference,
            ContextRecall,
        )
    except ImportError as e:
        print(f"ERROR: {e}")
        print("Instalá con: pip install -r scripts/requirements-eval.txt")
        sys.exit(1)

    dataset = json.loads(Path(dataset_path).read_text())
    if not dataset:
        print("ERROR: el dataset está vacío. Ejecutá generate_dataset.py primero.")
        sys.exit(1)

    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY no configurado en .env")
        sys.exit(1)

    print(f"Dataset:          {len(dataset)} muestras  ({dataset_path})")
    print(f"Embedding model:  {EMBEDDINGS_MODEL}")
    print(f"Groq model:       {GROQ_MODEL}")
    print(f"Top-k retrieval:  {top_k}\n")

    # LLM para pipeline RAG (generación de respuestas)
    # Permite override con EVAL_GEN_MODEL para evitar rate limits por modelo
    GEN_MODEL = os.getenv("EVAL_GEN_MODEL", GROQ_MODEL)
    print(f"Generation model:  {GEN_MODEL}")
    llm      = ChatGroq(model=GEN_MODEL, api_key=GROQ_API_KEY, temperature=0)
    st_model = SentenceTransformer(EMBEDDINGS_MODEL)

    # LLM para RAGAS como juez — necesita cliente async y un modelo que soporte JSON mode
    # qwen3.6-27b falla con instructor JSON schema; llama-3.3-70b-versatile funciona
    from groq import AsyncGroq
    RAGAS_JUDGE_MODEL = os.getenv("RAGAS_JUDGE_MODEL", "llama-3.3-70b-versatile")
    async_groq        = AsyncGroq(api_key=GROQ_API_KEY)
    instructor_client = instructor.from_groq(async_groq, mode=instructor.Mode.JSON)
    ragas_llm         = llm_factory(RAGAS_JUDGE_MODEL, provider="groq", client=instructor_client)
    print(f"RAGAS judge model: {RAGAS_JUDGE_MODEL}")
    ragas_emb          = RagasHFEmbeddings(model=EMBEDDINGS_MODEL)
    conn       = get_conn()

    print("Ejecutando pipeline RAG...\n")
    samples = []
    for i, item in enumerate(dataset):
        q = item["question"]
        print(f"[{i+1}/{len(dataset)}] {q[:75]}")
        contexts = retrieve(conn, st_model, q, top_k)
        answer   = generate(llm, q, contexts)
        samples.append(SingleTurnSample(
            user_input=q,
            retrieved_contexts=contexts,
            response=answer,
            reference=item["ground_truth"],
        ))
        print(f"  {len(contexts)} chunks | respuesta: {answer[:70]}...")

    conn.close()

    print(f"\nEjecutando RAGAS sobre {len(samples)} muestras...")
    faithfulness_m   = Faithfulness(llm=ragas_llm)
    answer_rel_m     = AnswerRelevancy(llm=ragas_llm, embeddings=ragas_emb)
    ctx_precision_m  = ContextPrecisionWithReference(llm=ragas_llm)
    ctx_recall_m     = ContextRecall(llm=ragas_llm)

    async def score_sample(s: SingleTurnSample) -> dict:
        scores = {}
        for name, coro in [
            ("faithfulness",              faithfulness_m.ascore(user_input=s.user_input, response=s.response, retrieved_contexts=s.retrieved_contexts)),
            ("answer_relevancy",          answer_rel_m.ascore(user_input=s.user_input, response=s.response)),
            ("context_precision",         ctx_precision_m.ascore(user_input=s.user_input, reference=s.reference, retrieved_contexts=s.retrieved_contexts)),
            ("context_recall",            ctx_recall_m.ascore(user_input=s.user_input, retrieved_contexts=s.retrieved_contexts, reference=s.reference)),
        ]:
            try:
                result = await coro
                scores[name] = float(result.score)
            except Exception as e:
                scores[name] = None
                print(f"    ⚠ {name}: {e}")
        return scores

    async def score_all() -> list[dict]:
        rows = []
        for i, s in enumerate(samples):
            print(f"  [{i+1}/{len(samples)}] scoring '{s.user_input[:60]}'...")
            row = await score_sample(s)
            row["question"] = s.user_input
            rows.append(row)
        return rows

    import asyncio
    rows = asyncio.run(score_all())

    import pandas as pd
    df = pd.DataFrame(rows)
    metric_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    means = df[metric_cols].mean()

    print("\n" + "=" * 58)
    print("  RESULTADOS RAGAS")
    print("=" * 58)
    for col in metric_cols:
        label = col.replace("_", " ").title()
        val   = means[col]
        bar   = "█" * int(val * 20) if not pd.isna(val) else "N/A"
        print(f"  {label:<35} {val:.3f}  {bar}")
    print("=" * 58)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "timestamp": timestamp,
        "config": {
            "embedding_model": EMBEDDINGS_MODEL,
            "groq_model":      GROQ_MODEL,
            "top_k":           top_k,
            "n_samples":       len(dataset),
            "dataset":         dataset_path,
        },
        "metrics": means.to_dict(),
        "per_sample": df.to_dict(orient="records"),
    }

    results_path = Path(f"scripts/results_{timestamp}.json")
    results_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    print(f"\n✓ Guardado en {results_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="scripts/dataset.json")
    parser.add_argument("--top-k",   type=int, default=4,
                        help="Chunks a recuperar por pregunta (default: 4)")
    args = parser.parse_args()

    if not Path(args.dataset).exists():
        print(f"ERROR: {args.dataset} no encontrado.")
        print("Generá el dataset con:  python scripts/generate_dataset.py")
        sys.exit(1)

    run(args.dataset, args.top_k)


if __name__ == "__main__":
    main()
