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

    # Controlar la cadencia de llamadas al juez RAGAS (para no exceder el
    # límite de requests/minuto del proveedor configurado):
    python scripts/eval_rag.py --dataset scripts/dataset.json --judge-rpm 15

    # Controlar también la cadencia de llamadas de generación a Groq (para no
    # exceder el límite de tokens/minuto del modelo de generación):
    python scripts/eval_rag.py --dataset scripts/dataset.json --judge-rpm 15 --gen-rpm 3

    # Comparar configuraciones:
    EMBEDDINGS_MODEL=paraphrase-multilingual-mpnet-base-v2 python scripts/eval_rag.py --top-k 6

Variables de entorno (desde .env):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    GROQ_API_KEY, GROQ_MODEL                  — LLM de generación del pipeline RAG
    GOOGLE_API_KEY o GEMINI_API_KEY           — juez RAGAS (Gemini, cualquiera de los dos nombres sirve)
    RAGAS_JUDGE_MODEL (default: gemini-3.1-flash-lite — gemini-3.6-flash pega el
        límite diario de 20 req del free tier casi de inmediato, flash-lite no)
    EMBEDDINGS_MODEL (default: paraphrase-multilingual-MiniLM-L12-v2)
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
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
EMBEDDINGS_MODEL  = os.getenv("EMBEDDINGS_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
# El SDK de Google no tiene un nombre de env var único: google-genai usa GOOGLE_API_KEY,
# pero muchos setups (incluido este .env) usan GEMINI_API_KEY. Soportamos ambos.
GOOGLE_API_KEY    = (_file.get("GOOGLE_API_KEY") or _file.get("GEMINI_API_KEY")
                      or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", ""))

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


def generate(llm: ChatGroq, question: str, contexts: list[str], max_retries: int = 5) -> str:
    from groq import RateLimitError

    ctx = "\n\n---\n\n".join(contexts) if contexts else "Sin contexto disponible."
    prompt = GENERATION_PROMPT.format(context=ctx, question=question)

    for attempt in range(max_retries):
        try:
            text = llm.invoke(prompt).content
            break
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait = getattr(getattr(e, "response", None), "headers", {}).get("retry-after")
            wait = float(wait) + 1 if wait else 2 ** attempt
            print(f"    ⚠ Rate limit, esperando {wait:.1f}s (intento {attempt + 1}/{max_retries})")
            time.sleep(wait)

    # qwen3.6-27b incluye <think>...</think> — removemos antes de pasar a RAGAS
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    return text


# ── Evaluación ──────────────────────────────────────────────────────────────

def run(dataset_path: str, top_k: int, judge_rpm: int, gen_rpm: int) -> None:
    try:
        from openai import AsyncOpenAI
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

    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY (o GEMINI_API_KEY) no configurado en .env")
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

    # LLM para RAGAS como juez — Gemini, pero hablándole con el protocolo de OpenAI.
    #
    # Gemini expone un endpoint compatible con la API de OpenAI
    # (https://generativelanguage.googleapis.com/v1beta/openai/), así que se puede usar
    # AsyncOpenAI apuntando a esa URL en vez del SDK nativo de Google (google-genai).
    #
    # La razón real de este approach es evitar un bug: con provider="google", el adapter
    # de ragas llama internamente a instructor.from_genai(client) sin pasar use_async=True,
    # lo que devuelve un cliente síncrono — incompatible con el resto del pipeline, que usa
    # .ascore()/.agenerate() en todo eval_rag.py. Eso revienta con
    # "TypeError: Cannot use agenerate() with a synchronous client".
    #
    # Con provider="openai", ragas usa instructor.from_openai(client) en su lugar, que sí
    # soporta clientes async correctamente. El modelo detrás sigue siendo Gemini — solo
    # cambia el protocolo con el que se le habla.
    RAGAS_JUDGE_MODEL  = os.getenv("RAGAS_JUDGE_MODEL", "gemini-3.1-flash-lite")
    async_google       = AsyncOpenAI(
        api_key=GOOGLE_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    # Default de ragas es max_tokens=1024 — insuficiente para el JSON de faithfulness
    # (lista de claims + veredicto por claim), lo vimos truncarse en la práctica.
    ragas_llm          = llm_factory(RAGAS_JUDGE_MODEL, provider="openai", client=async_google, max_tokens=4096)
    print(f"RAGAS judge model: {RAGAS_JUDGE_MODEL}")
    ragas_emb          = RagasHFEmbeddings(model=EMBEDDINGS_MODEL)
    conn       = get_conn()

    # Espaciado entre llamadas de generación para no exceder el límite de tokens/minuto
    # de Groq (qwen/qwen3.6-27b tiene 8000 TPM en esta cuenta, y cada llamada produce
    # salidas largas). x1.1 de margen para no quedar justo al filo del límite.
    gen_interval_seconds = (60 / gen_rpm) * 1.1
    print(f"Gen RPM:           {gen_rpm} (intervalo entre llamadas: {gen_interval_seconds:.1f}s)")

    print("Ejecutando pipeline RAG...\n")
    samples = []
    for i, item in enumerate(dataset):
        q = item["question"]
        print(f"[{i+1}/{len(dataset)}] {q[:75]}")
        contexts = retrieve(conn, st_model, q, top_k)
        print(f"  ⏳ esperando {gen_interval_seconds:.1f}s (gen-rpm={gen_rpm})")
        time.sleep(gen_interval_seconds)
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

    # Espaciado entre llamadas al juez para no exceder su límite de requests/minuto.
    # x1.1 de margen para no quedar justo al filo del límite.
    judge_interval_seconds = (60 / judge_rpm) * 1.1
    print(f"Judge RPM:         {judge_rpm} (intervalo entre llamadas: {judge_interval_seconds:.1f}s)\n")

    async def score_sample(s: SingleTurnSample) -> dict:
        scores = {}
        for name, coro in [
            ("faithfulness",              faithfulness_m.ascore(user_input=s.user_input, response=s.response, retrieved_contexts=s.retrieved_contexts)),
            ("answer_relevancy",          answer_rel_m.ascore(user_input=s.user_input, response=s.response)),
            ("context_precision",         ctx_precision_m.ascore(user_input=s.user_input, reference=s.reference, retrieved_contexts=s.retrieved_contexts)),
            ("context_recall",            ctx_recall_m.ascore(user_input=s.user_input, retrieved_contexts=s.retrieved_contexts, reference=s.reference)),
        ]:
            print(f"  ⏳ esperando {judge_interval_seconds:.1f}s (judge-rpm={judge_rpm})")
            await asyncio.sleep(judge_interval_seconds)
            try:
                result = await coro
                scores[name] = float(result.value)
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
    parser.add_argument("--judge-rpm", type=int, default=15,
                        help="Máximo de solicitudes por minuto al juez RAGAS (default: 15)")
    parser.add_argument("--gen-rpm",   type=int, default=3,
                        help="Máximo de solicitudes por minuto al modelo de generación (default: 3)")
    args = parser.parse_args()

    if not Path(args.dataset).exists():
        print(f"ERROR: {args.dataset} no encontrado.")
        print("Generá el dataset con:  python scripts/generate_dataset.py")
        sys.exit(1)

    run(args.dataset, args.top_k, args.judge_rpm, args.gen_rpm)


if __name__ == "__main__":
    main()
