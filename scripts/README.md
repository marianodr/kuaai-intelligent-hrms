# Scripts

## Datos de prueba

| Script | Qué hace |
|---|---|
| `seed-db.sh` | Carga empleados y asistencias de prueba. Ver README raíz. |
| `test-e2e.sh` | Prueba los 6 flujos principales del sistema end-to-end. |
| `generate_hr_docs.py` | Genera 4 PDFs de RRHH sintéticos en `docs/hr-pdfs/` (requiere `pip install reportlab`). |

## Evaluación del pipeline RAG (RAGAS)

```bash
pip install -r scripts/requirements-eval.txt

# 1. Generar el dataset "gold" (pregunta + respuesta esperada) a partir de los
#    documentos cargados en la DB
python scripts/generate_dataset.py [--chunks-per-doc 5] [--output scripts/dataset.json]

# 2. Evaluar el pipeline RAG contra ese dataset
python scripts/eval_rag.py [--dataset scripts/dataset.json] [--top-k 4]
```

Requiere el stack levantado (`docker compose up -d`) y `GROQ_API_KEY` +
(`GOOGLE_API_KEY` o `GEMINI_API_KEY`) configuradas en `.env`.

### Archivos

| Archivo | Contenido |
|---|---|
| `generate_dataset.py` | Genera el dataset "gold": samplea chunks de la DB y le pide al LLM una pregunta + respuesta esperada por chunk. |
| `eval_rag.py` | Corre retrieval + generación para cada pregunta del dataset y evalúa con RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall). |
| `dataset.json` | Dataset completo actual — 20 preguntas, 4 por cada uno de los 5 documentos RRHH-01 a RRHH-05 cargados en la DB. |
| `dataset_test.json` | Subconjunto de 5 preguntas (una por documento), para probar rápido que el pipeline de RAGAS funciona sin gastar la cuota diaria del juez. |
| `results_*.json` | Salida de cada corrida de `eval_rag.py` (scores + config). Generados localmente, no versionados (`.gitignore`). |
| `requirements-eval.txt` | Dependencias de este pipeline (`ragas`, `langchain-groq`, `openai`, `sentence-transformers`, etc). |

> Los datasets reflejan el estado de los documentos en la DB al momento de generarlos —
> si borrás o agregás documentos, regenerá el dataset con `generate_dataset.py` para que
> no queden preguntas apuntando a chunks que ya no existen.

### Modelos en uso actualmente

| Rol | Modelo | Variable de entorno |
|---|---|---|
| Generación (pipeline RAG, ambos scripts) | Groq — `qwen/qwen3.6-27b` | `GROQ_MODEL` |
| Embeddings (retrieval) | SentenceTransformers — `all-MiniLM-L6-v2` | `EMBEDDINGS_MODEL` |
| Juez RAGAS | Gemini — `gemini-3.1-flash-lite`, vía el endpoint OpenAI-compatible de Gemini | `RAGAS_JUDGE_MODEL`, `GOOGLE_API_KEY`/`GEMINI_API_KEY` |

`gemini-3.6-flash` (el modelo "grande" equivalente) también funciona técnicamente, pero
su free tier tiene un límite de 20 requests/día que se agota con muy pocas muestras —
`gemini-3.1-flash-lite` no tuvo ese problema en las pruebas. Ver
[`docs/decisions/ADR-004-groq-model-migration-qwen.md`](../docs/decisions/ADR-004-groq-model-migration-qwen.md)
para el contexto de por qué el modelo de generación es `qwen/qwen3.6-27b` y no un modelo Llama.
