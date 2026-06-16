# ADR-004 — Migración del modelo LLM a qwen/qwen3.6-27b

## Fecha
2026-06-16

## Contexto

Al intentar usar el agente RAG en producción, se detectó que el endpoint `/agent/chat`
devolvía error 500 con `code: tool_use_failed` al recibir preguntas que requerían
búsqueda en documentos (ej: "¿cómo se conforma el organigrama?").

La investigación reveló **tres problemas encadenados**:

### Problema 1 — System prompt corrompía el JSON del tool call

El system prompt incluía la regla:

> "Cuando uses la herramienta search_documents, al final de tu respuesta incluí una línea con el formato: `Fuentes: [nombre1, nombre2]`"

El modelo interpretaba esta instrucción durante la generación del tool call, produciendo:

```
<function=search_documents>{"query": "organigrama"} Fuentes: [Manual de Organización...]
```

El texto `Fuentes: [...]` aparecía dentro del campo `failed_generation` del error de Groq,
lo que hacía que el JSON de argumentos fuera inválido. La información de fuentes ya estaba
incluida en la respuesta de la herramienta misma (`[Fuente: nombre | similitud: X]`),
por lo que la instrucción era redundante además de dañina.

**Fix:** se eliminó la regla del system prompt.

### Problema 2 — API de Docling deprecada

La clase `DocumentConverter` de Docling cambió su interfaz entre versiones:

```python
# API antigua (rota):
DocumentConverter(pipeline_options=opts)

# API nueva (correcta):
DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
)
```

Esto causaba que el servidor FastAPI no arrancara cuando `DOCLING_OCR_ENABLED=true`.

**Fix:** se actualizaron los imports y la construcción del conversor en `ingestion.py`.

### Problema 3 — llama-3.1-8b-instant no soporta tool calling con 5+ herramientas

Incluso eliminando el bug del system prompt, el modelo `llama-3.1-8b-instant` generaba
tool calls en formato XML heredado (`<function=name>{args}`) en vez del JSON estándar
de Groq, causando el error 400 de la API. Al pasar a `llama-3.3-70b-versatile` (que sí
soporta tool calling), el error persistía cuando el agente tenía 5 o más herramientas
registradas, independientemente del tamaño o tipo de sus parámetros.

La investigación descartó múltiples hipótesis (schemas duplicados, parámetros `integer`,
longitud de descripciones) y concluyó que el límite es inherente a `llama-3.3-70b-versatile`
en la API de Groq para este volumen de herramientas.

## Modelos evaluados

| Modelo | Estado en Groq | Tool calling (6 tools) |
|--------|---------------|----------------------|
| `llama-3.1-8b-instant` | Activo | ❌ Formato XML incorrecto |
| `llama-3.3-70b-versatile` | Activo | ❌ Falla con 5+ tools |
| `llama3-groq-8b-8192-tool-use-preview` | **Decommissioned** | — |
| `llama3-groq-70b-8192-tool-use-preview` | **Decommissioned** | — |
| `llama-3.1-70b-versatile` | **Decommissioned** | — |
| `gemma2-9b-it` | **Decommissioned** | — |
| `meta-llama/llama-4-scout-17b-16e-instruct` | Activo | ❌ Ignora herramientas, responde en inglés |
| `qwen/qwen3-32b` | Activo | ⚠️ Llama la herramienta pero no aplica el resultado |
| `qwen/qwen3.6-27b` | Activo | ✅ Correcto con 6 tools, responde en español |

## Decisión

Se migra el modelo LLM de `llama-3.1-8b-instant` a **`qwen/qwen3.6-27b`**.

El cambio es una sola variable de entorno: `GROQ_MODEL=qwen/qwen3.6-27b`.

## Razones

1. **Es el único modelo activo en Groq** que soporta correctamente tool calling con las
   6 herramientas del agente Kuaai en el contexto de LangGraph.

2. **Sigue en Groq:** mantiene el tier gratuito y la integración `langchain-groq` sin
   cambios de proveedor.

3. **Calidad de respuesta:** las pruebas mostraron que el modelo sigue las instrucciones
   del system prompt (responder en español), usa los resultados de las herramientas
   correctamente y formatea las respuestas con markdown.

4. **Mismo cambio mínimo:** la integración LangChain no requiere modificar ningún código,
   solo el valor de `GROQ_MODEL`.

## Consecuencias

**Positivas:**
- Tool calling funciona correctamente con los 6 tools del agente
- Respuestas de mayor calidad que `llama-3.1-8b-instant` (27B vs 8B)
- Sin cambio de proveedor ni de código

**Negativas:**
- Modelo 27B es más lento que el 8B original (~2-3x)
- `qwen/qwen3.6-27b` es un modelo de terceros (Alibaba/Qwen) — menos transparencia
  que los modelos Meta/Llama
- Mayor consumo de rate limit de Groq por token

**Monitoreo:**
- Si Groq decomissiona `qwen/qwen3.6-27b`, la alternativa más directa sería
  `qwen/qwen3-32b` con un ajuste de prompts, u otra alternativa en el catálogo activo.
- La arquitectura LangChain/LangGraph permite cambiar el modelo con una sola línea:
  `ChatGroq(model=settings.groq_model, ...)` — el valor viene de la variable de entorno.

## Supersede

Este ADR supersede parcialmente ADR-003 en lo referente al modelo específico elegido.
La decisión de usar Groq como proveedor (vs OpenAI) sigue vigente.
