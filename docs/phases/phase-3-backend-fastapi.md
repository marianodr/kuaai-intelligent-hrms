# Phase 3 — Backend FastAPI + Agentic RAG

## Lo que se implementó

Backend de inteligencia artificial del sistema en FastAPI (Python). Implementa el pipeline completo de ingestión de documentos PDF y el agente RAG (Retrieval-Augmented Generation) que responde consultas en lenguaje natural sobre documentos empresariales y datos de asistencia.

- **Pipeline de ingestión:** PDF → Docling (extracción) → RecursiveCharacterTextSplitter (chunks) → SentenceTransformers (embeddings 384 dims) → pgvector (almacenamiento)
- **Agente LangChain:** `create_react_agent` con patrón ReAct, 6 herramientas especializadas, LLM Groq (Llama 3.1 8B)
- **Memoria de conversación:** `MemorySaver` de LangGraph con `thread_id` por usuario
- **Persistencia de historial:** tabla `chat_history` en PostgreSQL
- **Servicios singleton:** pool de conexiones psycopg2, cliente MinIO, modelo SentenceTransformer
- **Dockerfile** multi-stage; stage `production` pre-descarga el modelo de embeddings

---

## Estructura de routers y servicios

```
apps/backend-fastapi/
├── main.py                          # FastAPI app + lifespan (init DB, MinIO, modelo, agente)
├── requirements.txt                 # 15 dependencias Python
├── Dockerfile                       # Multi-stage: base → development → production
│
└── app/
    ├── config.py                    # Settings via pydantic-settings (lee .env)
    ├── database.py                  # ThreadedConnectionPool psycopg2 + context managers
    ├── minio_client.py              # Singleton Minio: download_to_bytes(), upload_bytes(), delete_object()
    ├── embeddings.py                # Singleton SentenceTransformer: get_embedding(), batch, to_pg_str()
    │
    ├── logging_config.py            # Logging centralizado (consola + archivo rotativo)
    ├── routers/
    │   ├── documents.py             # POST /documents/upload, /register, /process, GET /, /:id, DELETE /:id
    │   └── agent.py                 # POST /agent/chat, GET /agent/history/:user_id + manejo 429
    │
    ├── services/
    │   ├── ingestion.py             # process_document(): pipeline PDF → pgvector
    │   └── agent_service.py         # init_agent(), chat(), get_history()
    │
    └── tools/
        └── hrms_tools.py            # 3 @tool (un param) + 3 StructuredTool (multi-param) + ALL_TOOLS
```

**Dependencias clave (`requirements.txt`):**

| Librería | Versión mínima | Uso |
|----------|---------------|-----|
| `fastapi` | 0.115.0 | Framework web async |
| `uvicorn[standard]` | 0.30.0 | ASGI server |
| `psycopg2-binary` | 2.9.9 | Driver PostgreSQL |
| `pgvector` | 0.3.0 | Tipos vector para psycopg2 |
| `sentence-transformers` | 3.0.0 | Modelo de embeddings local |
| `docling` | 2.0.0 | Extracción de texto de PDFs |
| `minio` | 7.2.9 | Cliente object storage |
| `langchain` | 0.3.0 | Framework de agentes |
| `langchain-groq` | 0.2.0 | Integración con Groq API |
| `langchain-text-splitters` | 0.3.0 | RecursiveCharacterTextSplitter |
| `langgraph` | 1.2.0 | create_react_agent, MemorySaver |
| `pydantic-settings` | 2.3.0 | Configuración tipada desde .env |

---

## Pipeline de ingestión de documentos

El pipeline se ejecuta como **background task** de FastAPI para no bloquear la respuesta HTTP.

```
POST /documents/process { document_id }
          │
          ▼ (background task)
1. SELECT minio_path FROM documents WHERE id = document_id
          │
          ▼
2. MinIO: GET /{bucket}/{minio_path}  →  bytes del PDF
          │
          ▼
3. Docling: DocumentConverter().convert(tmp_file.pdf)
   → result.document.export_to_markdown()
   → texto completo del documento
          │
          ▼
4. RecursiveCharacterTextSplitter
   chunk_size=1000, chunk_overlap=100
   separators=["\n\n", "\n", ". ", " ", ""]
   → lista de N chunks de texto
          │
          ▼
5. SentenceTransformer('all-MiniLM-L6-v2')
   .encode(chunks, normalize_embeddings=True, batch_size=32)
   → N vectores de 384 dimensiones
          │
          ▼
6. DELETE document_chunks WHERE document_id = X  (limpia reprocesos)
   INSERT document_chunks (document_id, content, embedding::vector, chunk_index)
          │
          ▼
7. UPDATE documents SET status = 'READY' WHERE id = document_id
```

**Estados del documento:**
- `PROCESSING` → asignado al crear el registro y al inicio del pipeline
- `READY` → pipeline completado exitosamente
- `ERROR` → excepción durante el pipeline (se loguea el error)

---

## Herramientas del agente (tabla completa)

Ver detalle completo en [docs/architecture/agent-tools.md](../architecture/agent-tools.md).

| Herramienta | Parámetros | Fuente de datos | Cuándo se usa |
|---|---|---|---|
| `search_documents` | `query: str` | pgvector (cosine similarity) | Preguntas sobre políticas, reglamentos, manuales |
| `get_daily_attendance` | `date: str` (YYYY-MM-DD) | `attendance_records` | "¿Quiénes vinieron hoy?" |
| `get_employee_attendance` | `employee_id: int, month: int, year: int` | `attendance_records` | "¿Cómo fue la asistencia de García en abril?" |
| `get_tardiness_report` | `month: int, year: int` | `attendance_records` | "¿Quiénes llegaron tarde este mes?" |
| `get_monthly_summary` | `month: int, year: int` | `attendance_records` | "¿Cuál fue el porcentaje de asistencia en mayo?" |
| `get_employee_info` | `query: str` | `employees` | "¿Cuál es el legajo de María López?" |

---

## Endpoints expuestos

### Documents

| Método | Ruta | Body | Descripción |
|--------|------|------|-------------|
| `POST` | `/documents/upload` | `multipart: file, uploaded_by` | Sube PDF a MinIO y registra en DB. Retorna `{ document_id }` |
| `POST` | `/documents/process` | `{ document_id }` | Dispara pipeline en background (responde 200 inmediatamente) |
| `POST` | `/documents/register` | `{ name, minio_path, uploaded_by }` | Registra documento ya alojado en MinIO (uso interno/NestJS) |
| `GET` | `/documents/` | — | Lista todos los documentos con estado |
| `GET` | `/documents/{id}` | — | Detalle de un documento |
| `DELETE` | `/documents/{id}` | — | Elimina documento, chunks (CASCADE) y archivo de MinIO |

### Agent

| Método | Ruta | Body | Descripción |
|--------|------|------|-------------|
| `POST` | `/agent/chat` | `{ question, user_id, thread_id? }` | Consulta al agente RAG. Retorna `{ answer, thread_id }` |
| `GET` | `/agent/history/{user_id}` | — | Historial de conversación desde DB. Query: `?limit=50` |

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check básico |

---

## Flujo del agente RAG

```
POST /agent/chat { question: "¿Quiénes llegaron tarde en mayo?", user_id: 1 }
          │
          ▼
agent_service.chat(question, user_id, thread_id="user-1")
          │
          ▼
create_react_agent.invoke(
  {
    "messages": [
      { "role": "system", "content": system_prompt },   # incluye fecha de hoy
      { "role": "user", "content": question }
    ]
  },
  config={ configurable: { thread_id }, recursion_limit: 25 }
)
          │
          ▼
[Iteración 1] ChatGroq analiza el mensaje
  → decide llamar: get_tardiness_report(month=5, year=2026)
          │
          ▼
[Tool execution] SQL:
  SELECT e.first_name, e.last_name, COUNT(*) as tardanzas
  FROM attendance_records ar JOIN employees e ...
  WHERE is_late = true AND month = 5 AND year = 2026
  GROUP BY e.id ORDER BY tardanzas DESC
          │
          ▼
[Iteración 2] ChatGroq recibe resultado JSON
  → genera respuesta en lenguaje natural en español
          │
          ▼
answer = result["messages"][-1].content
          │
          ├── INSERT chat_history (user_id, 'user', question)
          └── INSERT chat_history (user_id, 'assistant', answer)
          │
          ▼
{ answer: "En mayo 2026, los empleados con más tardanzas fueron...", thread_id: "user-1" }
```

---

## Cómo probarlo

### Iniciar el servicio

```bash
cd apps/backend-fastapi
pip install -r requirements.txt
cp ../../.env.example ../../.env   # asegurarse de tener GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

### Documentación interactiva (Swagger)

```
http://localhost:8000/docs
```

### Subir y procesar un documento

```bash
# 1. Subir el PDF (sube a MinIO y registra en DB en un solo paso)
RESPONSE=$(curl -s -X POST http://localhost:8000/documents/upload \
  -F "file=@/ruta/al/Reglamento_Interno.pdf" \
  -F "uploaded_by=1")
# Respuesta: { "document_id": "uuid-xxx" }

DOC_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['document_id'])")

# 2. Disparar el pipeline de ingestión en background
curl -X POST http://localhost:8000/documents/process \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$DOC_ID\"}"
# Respuesta: { "message": "Procesamiento iniciado", "document_id": "uuid-xxx" }

# 3. Verificar el estado (esperar 10-60 segundos según tamaño del PDF)
curl http://localhost:8000/documents/$DOC_ID
# Respuesta: { ..., "status": "READY" }
```

### Consultas al agente RAG

```bash
# Pregunta sobre documentos
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuál es la política de licencias por enfermedad?",
    "user_id": 1
  }'

# Pregunta sobre asistencia del día
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuántos empleados vinieron hoy?",
    "user_id": 1,
    "thread_id": "user-1"
  }'

# Pregunta sobre tardanzas del mes
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Quiénes llegaron tarde en mayo de 2026?",
    "user_id": 1,
    "thread_id": "user-1"
  }'

# Buscar información de un empleado
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuál es el legajo de García?",
    "user_id": 1,
    "thread_id": "user-1"
  }'

# Ver historial de conversación
curl http://localhost:8000/agent/history/1?limit=20
```

---

## Decisiones técnicas tomadas

### Groq sobre OpenAI
Se eligió Groq por su API gratuita (con límites generosos para un MVP académico) y la disponibilidad de Llama 3.1 8B con soporte nativo de tool calling. Ver [ADR-003](../decisions/ADR-003-groq-vs-openai.md).

### SentenceTransformers local sobre embeddings de API
El modelo `all-MiniLM-L6-v2` corre localmente dentro del contenedor. Esto evita costos por embedding, latencia de red y dependencia de API externa para el pipeline de ingestión. El modelo pesa ~90MB y genera vectores de 384 dimensiones, compatibles con el índice `ivfflat` configurado en pgvector.

### RecursiveCharacterTextSplitter (1000/100)
Siguiendo el patrón recomendado por el skill `langchain-rag`: chunk_size=1000 con chunk_overlap=100 (~10%). Los separators priorizan párrafos (`\n\n`), luego líneas, luego oraciones. Evita cortar en medio de conceptos clave de documentos empresariales.

### `create_react_agent` de LangGraph
El agente usa el patrón ReAct (Reasoning + Acting): el LLM razona sobre qué herramienta usar, la ejecuta, observa el resultado y decide el próximo paso. `MemorySaver` mantiene el historial de conversación en memoria por `thread_id`, y la DB `chat_history` persiste para consulta histórica desde el frontend.

**System prompt en `invoke()`:** el prompt de sistema se inyecta en cada llamada a `invoke()` como mensaje `role: "system"`, junto con la fecha de hoy. No se pasa al constructor de `create_react_agent` porque la fecha debe ser dinámica.

**`recursion_limit: 25`:** cada ciclo think→act del agente consume 2 nodos en el grafo LangGraph. Con 6 herramientas disponibles y consultas que requieren 2-3 herramientas en cadena, el límite de 15 (original) era insuficiente.

**`max_retries=0` en ChatGroq:** el SDK de Groq reintenta con backoff exponencial ante rate limits. En el tier gratuito (6.000 TPM), esto puede bloquear el request por minutos. Con `max_retries=0`, el error es inmediato y el router devuelve `429` con un mensaje claro al usuario.

### `StructuredTool` para herramientas multi-parámetro
El decorator `@tool` de LangChain no genera schemas JSON correctos para herramientas con múltiples parámetros enteros cuando se usa con `langchain-groq`. El modelo recibe un schema malformado y genera llamadas en formato XML (`<function=nombre>{...}`) en lugar de JSON, causando `tool_use_failed` en la Groq API.

Solución: las tres herramientas con múltiples parámetros numéricos (`get_employee_attendance`, `get_tardiness_report`, `get_monthly_summary`) usan `StructuredTool.from_function()` con un `BaseModel` de Pydantic como `args_schema`. Las herramientas de un solo parámetro string siguen usando `@tool`.

Adicionalmente, las secciones `Args:` de estilo Google en los docstrings también causaban schemas malformados. Los docstrings de todas las herramientas usan descripción plana sin secciones estructuradas.

### Logging centralizado (`logging_config.py`)
`setup_logging(log_level, log_file)` configura dos handlers: consola (nivel configurable vía `LOG_LEVEL`) y archivo rotativo de 10 MB (nivel DEBUG siempre). Librerías ruidosas como `docling`, `transformers` y `sentence_transformers` se silencian a WARNING para mantener los logs legibles durante el desarrollo.

### Background tasks para ingestión
El pipeline de ingestión puede tardar varios segundos (Docling es pesado con PDFs grandes). Usar `BackgroundTasks` de FastAPI permite responder `200 OK` inmediatamente al NestJS y procesar en background, con el estado del documento reflejado en la DB (`PROCESSING` → `READY`).

### psycopg2 sobre asyncpg
Se eligió psycopg2 con `ThreadedConnectionPool` en lugar de asyncpg para evitar complejidad adicional de async en los tools de LangChain, que son funciones síncronas. Los endpoints FastAPI que llaman a estas funciones bloqueantes son manejables dado el volumen esperado de un MVP.

---

## Pendientes para fases siguientes

- [x] **Fase 4:** El frontend Next.js consume `POST /agent/chat` y `GET /agent/history/:user_id` vía NestJS (proxy)
- [x] **Fase 4:** Upload de PDFs: el frontend sube a NestJS `POST /documents/upload` → NestJS hace proxy a FastAPI → FastAPI almacena en MinIO y registra en DB → frontend llama a `/documents/process` vía NestJS
- [ ] Streaming de respuesta del agente (Server-Sent Events) para UX más fluida
- [ ] Migrar MemorySaver a PostgreSQL checkpointer (`langgraph-checkpoint-postgres`) para persistencia entre reinicios
- [ ] Manejo de PDFs muy grandes: dividir en páginas antes de pasar a Docling
- [ ] Límite de tokens en el contexto del agente: truncar historial largo antes de invocar
- [ ] Tests de integración para cada herramienta del agente
