# Evaluación de sistemas RAG: RAGAS y metodología

## ¿Es una práctica común?

Sí. A medida que los sistemas RAG pasaron de demos a producción, la evaluación sistemática se volvió estándar. El problema central es que un RAG tiene dos subsistemas que pueden fallar de forma independiente:

- **Retrieval** — ¿se recuperan los chunks relevantes?
- **Generation** — ¿el modelo usa correctamente los chunks recuperados?

Una respuesta incorrecta puede venir de un retrieval pobre (recuperó contexto irrelevante) o de una generación pobre (tenía el contexto correcto pero lo ignoró). Sin métricas separadas para cada subsistema, no sabés dónde está el problema.

---

## RAGAS

**RAGAS** (Retrieval Augmented Generation Assessment) es el framework más adoptado. Evalúa el pipeline completo con métricas automáticas usando un LLM como juez.

### Métricas principales

| Métrica | Qué mide | Subsistema |
|---------|----------|------------|
| **Context Precision** | ¿Qué porcentaje de los chunks recuperados son relevantes para la pregunta? | Retrieval |
| **Context Recall** | ¿Qué porcentaje de la respuesta esperada está cubierto por los chunks recuperados? | Retrieval |
| **Faithfulness** | ¿La respuesta generada se basa en el contexto, o el modelo inventó datos? | Generation |
| **Answer Relevancy** | ¿La respuesta responde directamente la pregunta? | Generation |

Cada métrica devuelve un score entre 0 y 1. Se puede calcular por separado o como un score combinado.

### Dependencias

RAGAS necesita un LLM para calcular las métricas (actúa como juez). Puede usarse Groq (el mismo que ya tenemos) o cualquier modelo compatible con LangChain.

### Instalación

```bash
pip install ragas langchain-groq
```

---

## Alternativas a RAGAS

| Framework | Enfoque | Cuándo usarlo |
|-----------|---------|---------------|
| **RAGAS** | Evaluación completa del pipeline RAG | Caso general, bien documentado |
| **TruLens** | Evaluación + trazabilidad visual | Si querés UI de monitoreo |
| **DeepEval** | Suite amplia, incluye unit tests para LLMs | Si ya tenés una cultura de testing formal |
| **LlamaIndex Eval** | Integrado en LlamaIndex | Si el stack usa LlamaIndex |
| **Promptfoo** | Comparación de prompts y modelos | Si el foco es el prompt engineering |

Para el stack actual (LangChain + FastAPI + Groq), RAGAS es la opción más directa.

---

## Metodología: cómo evaluar configuraciones

### Paso 1 — Construir el dataset de evaluación

El dataset es la base de todo. Cada entrada tiene:

```python
{
    "question": "¿Cuántos días de licencia por paternidad corresponden?",
    "ground_truth": "El reglamento establece 5 días hábiles de licencia por paternidad.",
    "ground_truth_context": ["...texto del chunk relevante..."]  # opcional
}
```

**Cómo generarlo:**
- **Manual**: preguntas reales que haría un empleado sobre los documentos cargados. Es el gold standard pero costoso.
- **LLM-asistido**: pedirle al modelo que genere preguntas a partir de cada chunk. Más rápido, pero hay que revisar la calidad.

Mínimo viable: 20–30 preguntas que cubran todos los documentos cargados.

### Paso 2 — Definir las configuraciones a comparar

Los hiperparámetros más impactantes en un RAG son:

| Hiperparámetro | Valores típicos a probar | Impacto |
|----------------|--------------------------|---------|
| **Modelo de embeddings** | MiniLM-L6, multilingual-mpnet, e5-large | Alto |
| **Chunk size** | 256, 512, 1024 tokens | Alto |
| **Chunk overlap** | 0, 50, 100 tokens | Medio |
| **Top-k chunks recuperados** | 3, 5, 8 | Medio |
| **Modelo de generación** | qwen3.6-27b, llama-4, etc. | Alto |
| **Umbral de similitud mínima** | sin umbral, 0.2, 0.3 | Bajo–medio |

### Paso 3 — Ejecutar la evaluación

Para cada configuración:

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

# dataset con preguntas, respuestas generadas y contextos recuperados
result = evaluate(
    dataset=Dataset.from_list(samples),
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    llm=groq_llm,
    embeddings=embedding_model,
)

print(result)
# {'faithfulness': 0.82, 'answer_relevancy': 0.78, 'context_precision': 0.71, 'context_recall': 0.65}
```

### Paso 4 — Comparar y decidir

| Configuración | Context Precision | Context Recall | Faithfulness | Answer Relevancy |
|--------------|:-----------------:|:--------------:|:------------:|:----------------:|
| MiniLM-L6 / chunk 512 / k=4 | 0.48 | 0.52 | 0.74 | 0.70 |
| multilingual-mpnet / chunk 512 / k=4 | 0.61 | 0.65 | 0.78 | 0.75 |
| multilingual-mpnet / chunk 256 / k=6 | 0.58 | 0.70 | 0.75 | 0.73 |

No siempre hay un ganador claro en todas las métricas. La prioridad depende del caso de uso:
- Si los usuarios hacen preguntas factuales (licencias, procedimientos), priorizar **Faithfulness** y **Context Recall**.
- Si el agente necesita responder con precisión sin inventar, priorizar **Faithfulness**.

---

## Aplicación concreta a Kuaai

### Hipótesis a validar

1. **¿El modelo de embeddings en español mejora los scores?**
   Comparar `all-MiniLM-L6-v2` vs `paraphrase-multilingual-mpnet-base-v2` con el mismo dataset.

2. **¿El chunk size actual es óptimo?**
   Los chunks actuales parecen tener entre 200 y 1000 chars (~50–250 tokens). Probar tamaños fijos (512 tokens) podría dar retrieval más predecible.

3. **¿k=4 es suficiente?**
   Si Context Recall es bajo, aumentar a k=6 u 8 y ver si mejora sin degradar Faithfulness.

### Flujo sugerido

```
1. Generar 30 preguntas con LLM a partir de los PDFs existentes
2. Correr baseline: MiniLM-L6 / chunk actual / k=4
3. Correr variante: multilingual-mpnet / chunk actual / k=4
4. Si hay mejora en retrieval → probar variaciones de chunk size
5. Fijar la mejor combinación de embeddings + chunking
6. Probar k=4 vs k=6 sobre esa combinación
7. Documentar configuración ganadora
```

### Costo estimado

- Dataset de 30 preguntas: ~30 min de trabajo manual o 5 min con LLM
- Cada corrida de RAGAS sobre 30 preguntas: ~5 min, ~200 llamadas al LLM juez
- Con Groq en free tier: factible sin costo adicional

---

## Limitaciones a tener en cuenta

- **RAGAS usa un LLM como juez**, por lo que la calidad de la evaluación depende de ese modelo. Un modelo débil puede dar métricas engañosas.
- **El dataset de evaluación es crítico**: si las preguntas no representan el uso real, los resultados no son útiles.
- **Cambiar el modelo de embeddings invalida todos los índices existentes**: requiere re-ingestar todos los documentos y puede requerir una migración de DB si cambian las dimensiones del vector.
- **No es un proceso de una sola vez**: lo ideal es re-evaluar cuando se agregan documentos nuevos o se cambia el modelo de generación.
