#!/usr/bin/env python3
"""
Evaluación del pipeline RAG con RAGAS.

Requiere:
    pip install -r scripts/requirements-eval.txt

Uso:
    python scripts/eval_rag.py

Variables de entorno (desde .env):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    GROQ_API_KEY
    EMBEDDINGS_MODEL
"""

import os
import sys
import json
from pathlib import Path

# Agregar el directorio del backend FastAPI al path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend-fastapi"))

from dotenv import load_dotenv
load_dotenv()

from app.config import settings
from app import database, embeddings as emb_service
from app.tools.hrms_tools import search_documents
from app.services.agent_service import init_agent, chat

# ─── Dataset de evaluación ────────────────────────────────────────────────────
# Pares pregunta/respuesta esperada sobre los documentos HR cargados.
# Ampliar con más casos para una evaluación robusta.
EVAL_DATASET = [
    {
        "question": "¿Cuántos días de vacaciones corresponden por año?",
        "ground_truth": "La política de vacaciones define los días según antigüedad.",
    },
    {
        "question": "¿Cuál es el procedimiento para solicitar una licencia médica?",
        "ground_truth": "El empleado debe presentar certificado médico al área de RRHH.",
    },
    {
        "question": "¿Qué documentación se requiere para el proceso de contratación?",
        "ground_truth": "Se requiere DNI, CUIL, antecedentes penales y referencias laborales.",
    },
]


def retrieve_context(question: str, k: int = 4) -> list[str]:
    """Recupera contexto usando el tool search_documents."""
    emb_service.init_model(settings.embeddings_model)
    database.init_pool(settings)
    raw = search_documents.invoke({"query": question})
    # El tool ahora retorna texto con headers [Fuente: ...]
    return [raw] if raw else []


def run_ragas_evaluation() -> None:
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_recall
        from datasets import Dataset
    except ImportError:
        print("ERROR: instalá las dependencias con: pip install -r scripts/requirements-eval.txt")
        sys.exit(1)

    database.init_pool(settings)
    emb_service.init_model(settings.embeddings_model)
    init_agent(settings)

    records = []
    for item in EVAL_DATASET:
        question = item["question"]
        print(f"\nEvaluando: {question!r}")

        contexts = retrieve_context(question)
        answer = chat(question, user_id=0, thread_id="eval-thread")

        records.append({
            "question": question,
            "answer": answer,
            "contexts": contexts,
            "ground_truth": item["ground_truth"],
        })
        print(f"  Respuesta: {answer[:100]}...")

    dataset = Dataset.from_list(records)
    result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_recall])

    print("\n" + "=" * 60)
    print("RAGAS Evaluation Results")
    print("=" * 60)
    print(json.dumps(result.to_pandas().mean().to_dict(), indent=2, ensure_ascii=False))

    database.close_pool()


if __name__ == "__main__":
    run_ragas_evaluation()
