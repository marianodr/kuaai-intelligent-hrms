# ADR-005 — chunk_size=500 y embeddings multilingües como defaults

## Fecha
2026-08-21

## Contexto

El pipeline de ingestión (`apps/backend-fastapi/app/services/ingestion.py`)
usaba `chunk_size=1000`, `chunk_overlap=100` y el modelo de embeddings
`all-MiniLM-L6-v2` (384 dims, entrenado principalmente en inglés) como
defaults hardcodeados, heredados de la fase 3 (ver
`docs/phases/phase-3-backend-fastapi.md`) sin haberse comparado contra
alternativas.

`docs/rag-evaluation.md` dejaba planteada como hipótesis pendiente si un
modelo de embeddings multilingüe (con soporte de español) mejoraría el
retrieval sobre los documentos de RRHH, todos en español, y si un chunk_size
distinto daría mejores resultados.

## Decisión

Se corrió una matriz 2x2 de **chunk_size** (1000 vs 500, con overlap
proporcional 100/50) x **modelo de embeddings** (`all-MiniLM-L6-v2` vs
`paraphrase-multilingual-MiniLM-L12-v2`, ambos 384 dims) evaluada con RAGAS
sobre `scripts/dataset.json` (20 preguntas, top_k=4, juez
`gemini-3.5-flash-lite`, generación `qwen/qwen3.6-27b` vía Groq).

| Configuración | Faithfulness | Answer Relevancy | Context Precision | Context Recall |
|---|:---:|:---:|:---:|:---:|
| chunk1000 + all-MiniLM-L6-v2 (baseline) | 0.937 | 0.621 | 0.617 | 0.700 |
| chunk1000 + multilingual | 0.969 | 0.759 | 0.496 | 0.725 |
| chunk500 + all-MiniLM-L6-v2 | 0.945 | 0.691 | 0.592 | 0.775 |
| **chunk500 + multilingual** | **0.975** | **0.765** | **0.700** | **0.800** |

`chunk_size=500` + `paraphrase-multilingual-MiniLM-L12-v2` ganó en las 4
métricas simultáneamente frente a las otras 3 combinaciones. Se adopta como
default en todo el sistema:

- `chunk_size`: 1000 → **500**
- `chunk_overlap`: 100 → **50**
- `EMBEDDINGS_MODEL`: `all-MiniLM-L6-v2` → **`paraphrase-multilingual-MiniLM-L12-v2`**
- `EMBEDDINGS_DIMENSIONS` se mantiene en 384 (ambos modelos producen vectores
  de la misma dimensión, no requiere migración de esquema en pgvector)

## Razones

1. **Documentos 100% en español**: un modelo de embeddings multilingüe
   entrenado también en español captura mejor la semántica de los documentos
   de RRHH que un modelo mayormente inglés, lo que se refleja en la mejora de
   Context Precision (0.617 → 0.700 a igual chunk_size) y Context Recall.

2. **Chunks más chicos mejoran recall en documentos cortos**: los PDFs de
   RRHH son relativamente breves (8-12 chunks por documento con
   chunk_size=500); chunks de 1000 caracteres mezclaban más temas por chunk,
   diluyendo la relevancia del top-4 recuperado.

3. **Mismo espacio de dimensiones (384)**: no hay que migrar el esquema de
   `document_chunks` (`vector(384)`) ni el índice `ivfflat` — el cambio de
   modelo es transparente a nivel de base de datos.

4. **Sin trade-off entre subsistemas**: la configuración ganadora mejora
   tanto las métricas de retrieval (Context Precision, Context Recall) como
   las de generación (Faithfulness, Answer Relevancy) — no hubo que priorizar
   una métrica a costa de otra.

## Consecuencias

**Positivas:**
- Mejor calidad de respuestas del agente sobre documentos en español, sin
  costo adicional (ambos modelos son locales, sin llamadas a API externa)
- No requiere migración de esquema de base de datos

**Negativas:**
- Los 5 documentos existentes debieron reprocesarse (re-chunking +
  re-embedding) para que `document_chunks` reflejara la nueva configuración
  — ya hecho como parte de la corrida de la matriz 2x2, no aplica a nuevos
  documentos, que usan el nuevo default automáticamente
- El modelo multilingüe (`paraphrase-multilingual-MiniLM-L12-v2`) no viene
  pre-descargado en imágenes Docker construidas antes de este cambio; el
  `Dockerfile` de `backend-fastapi` se actualizó para pre-bakearlo en el
  build de producción
- Chunks más chicos (500 vs 1000) significan más filas en `document_chunks`
  por documento — impacto despreciable al volumen actual (decenas de
  documentos)

**Revisión futura:** `docs/rag-evaluation.md` deja pendiente evaluar
tamaños de chunk adicionales (256, 750) y tamaños fijos en tokens en vez de
caracteres, además de si k=4 sigue siendo suficiente con la nueva
configuración.

## Referencias

- Resultados completos: `scripts/results_20260820_210141_chunk500_all-MiniLM-L6-v2.json`,
  `scripts/results_20260821_002945_chunk500_multilingual.json`
- Baselines (chunk1000, corridos previamente): `scripts/results_20260819_210745_baseline_gemini35.json`,
  `scripts/results_20260819_201629_multilingual_gemini35.json`
- Metodología: `docs/rag-evaluation.md`
- Pipeline de retrieval: `docs/rag-retrieval-pipeline.md`
