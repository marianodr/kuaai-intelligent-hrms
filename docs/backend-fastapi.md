# Backend FastAPI — Kuaai Intelligent HRMS

## Índice

1. [Propósito y responsabilidades](#1-propósito-y-responsabilidades)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura de archivos](#3-estructura-de-archivos)
4. [Configuración y entorno](#4-configuración-y-entorno)
5. [Arranque de la aplicación](#5-arranque-de-la-aplicación)
6. [Base de datos](#6-base-de-datos)
7. [Almacenamiento de archivos — MinIO](#7-almacenamiento-de-archivos--minio)
8. [Embeddings vectoriales](#8-embeddings-vectoriales)
9. [Routers y endpoints](#9-routers-y-endpoints)
10. [Servicios](#10-servicios)
11. [Herramientas del agente IA](#11-herramientas-del-agente-ia)
12. [Esquema de base de datos](#12-esquema-de-base-de-datos)
13. [Flujos completos](#13-flujos-completos)
14. [Docker](#14-docker)
15. [Variables de entorno](#15-variables-de-entorno)

---

## 1. Propósito y responsabilidades

El backend FastAPI es el servicio de inteligencia artificial del HRMS. No gestiona autenticación ni usuarios (eso es responsabilidad del backend NestJS); su foco es exclusivamente:

- **Ingestión de documentos:** recibir PDFs desde MinIO, extraer texto, generar embeddings y almacenarlos en PostgreSQL con pgvector.
- **Agente conversacional RAG:** responder preguntas en lenguaje natural sobre documentos empresariales y datos de asistencia, utilizando un agente LangGraph con herramientas especializadas.

Este servicio es llamado por el backend NestJS y por el frontend Next.js, nunca expuesto directamente al usuario final sin autenticación previa en NestJS.

---

## 2. Stack tecnológico

| Componente | Tecnología | Versión mínima |
|---|---|---|
| Framework web | FastAPI + Uvicorn | 0.115 / 0.30 |
| Validación | Pydantic v2 | 2.7 |
| Base de datos | PostgreSQL + psycopg2 | pg 15+ |
| Búsqueda vectorial | pgvector | 0.3 |
| Almacenamiento de archivos | MinIO | 7.2 |
| Extracción de texto de PDFs | Docling | 2.0 |
| Chunking de texto | LangChain Text Splitters | 0.3 |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`) | 3.0 |
| LLM | Groq (llama-3.1-8b-instant) | — |
| Agente IA | LangGraph ReAct | 0.2 |
| Definición de herramientas | LangChain Core | 0.3 |

### Por qué Groq en lugar de OpenAI

La decisión está documentada en `docs/decisions/ADR-003`. Groq ofrece inferencia extremadamente rápida sobre modelos open source (Llama) a un costo significativamente menor que OpenAI, lo que es adecuado para un MVP donde la velocidad de respuesta es prioritaria y el volumen de tokens es moderado.

---

## 3. Estructura de archivos

```
apps/backend-fastapi/
├── main.py                    # Punto de entrada de la aplicación
├── requirements.txt           # Dependencias Python
├── Dockerfile                 # Imagen Docker (dev y prod)
└── app/
    ├── config.py              # Settings via pydantic-settings
    ├── database.py            # Pool de conexiones PostgreSQL
    ├── minio_client.py        # Cliente MinIO (upload/download)
    ├── embeddings.py          # Modelo SentenceTransformers
    ├── routers/
    │   ├── documents.py       # Endpoints CRUD + procesamiento de docs
    │   └── agent.py           # Endpoint de chat y historial
    ├── services/
    │   ├── ingestion.py       # Pipeline: PDF → texto → chunks → pgvector
    │   └── agent_service.py   # Inicialización y ejecución del agente LangGraph
    └── tools/
        └── hrms_tools.py      # Herramientas LangChain para el agente
```

---

## 4. Configuración y entorno

`app/config.py` usa **pydantic-settings** para leer variables de entorno y `.env`. Todas las configuraciones tienen valores por defecto excepto `GROQ_API_KEY`, que es obligatoria.

```python
class Settings(BaseSettings):
    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "kuaai"
    postgres_user: str = "kuaai_user"
    postgres_password: str = "kuaai_password"

    # MinIO
    minio_endpoint: str = "minio"
    minio_port: int = 9000
    minio_access_key: str = "kuaai_access"
    minio_secret_key: str = "kuaai_secret"
    minio_bucket_documents: str = "documents"

    # Groq
    groq_api_key: str          # OBLIGATORIO — sin default
    groq_model: str = "llama-3.1-8b-instant"

    # SentenceTransformers
    embeddings_model: str = "all-MiniLM-L6-v2"
    embeddings_dimensions: int = 384

    class Config:
        env_file = ".env"
        case_sensitive = False
```

El objeto `settings` es un singleton importado donde se necesita: `from app.config import settings`.

---

## 5. Arranque de la aplicación

`main.py` define el ciclo de vida de la aplicación usando el patrón `lifespan` de FastAPI (introducido en FastAPI 0.93, reemplaza los eventos `startup`/`shutdown`).

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_pool(settings)        # Abre el pool de conexiones PG
    minio_client.init_client(settings)  # Conecta MinIO
    emb_service.init_model(settings.embeddings_model)  # Carga modelo de embeddings a RAM
    init_agent(settings)                # Inicializa LLM + LangGraph
    yield
    database.close_pool()               # Cierra conexiones al detener
```

El bloque antes del `yield` es el startup; el bloque después es el shutdown. Esto garantiza que si falla cualquier inicialización, la aplicación no arranca.

La aplicación registra dos routers y un endpoint de salud:

```
GET  /health            → {"status": "ok"}
*    /documents/*       → routers/documents.py
*    /agent/*           → routers/agent.py
```

El CORS está configurado con `allow_origins=["*"]` para el MVP. En producción debería restringirse a los orígenes del frontend y de NestJS.

---

## 6. Base de datos

`app/database.py` implementa un **pool de conexiones** con `psycopg2.pool.ThreadedConnectionPool`, apto para el modelo multi-thread de Uvicorn con workers síncronos.

### Pool

```python
_pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host=..., port=..., dbname=..., user=..., password=...
)
```

El pool mantiene entre 1 y 10 conexiones abiertas. FastAPI las toma del pool cuando llega un request y las devuelve al terminar.

### Context managers

Hay dos formas de usar la base de datos:

**`get_conn()`** — entrega una conexión completa. Útil cuando se necesita manejar múltiples cursores dentro de la misma transacción.

```python
with database.get_conn() as conn:
    cur = conn.cursor()
    ...
```

**`get_cursor(dict_cursor=True)`** — el más usado. Abre conexión + cursor en un solo bloque. Con `dict_cursor=True` (el default) las filas devueltas son diccionarios accesibles por nombre de columna en lugar de por índice.

```python
with database.get_cursor() as (cur, conn):
    cur.execute("SELECT * FROM employees WHERE id = %s", (emp_id,))
    row = cur.fetchone()
    print(row["first_name"])  # acceso por nombre
```

El rollback automático ante excepciones está implementado en `get_conn()`, lo que protege las transacciones de dejar datos corruptos si un handler falla a mitad de camino.

---

## 7. Almacenamiento de archivos — MinIO

`app/minio_client.py` encapsula las operaciones con MinIO (storage compatible con S3).

MinIO es quien actúa como source of truth para los PDFs originales. La base de datos solo guarda la ruta (`minio_path`) para saber de dónde descargar el archivo cuando se necesite procesar.

### Operaciones disponibles

**`download_to_bytes(object_name)`** — descarga un objeto de MinIO y lo devuelve como `bytes`. Cierra la conexión HTTP correctamente después de leer.

```python
pdf_bytes = minio_client.download_to_bytes("docs/politica-vacaciones.pdf")
```

**`upload_bytes(object_name, data, content_type)`** — sube bytes a MinIO. Usado por NestJS para el upload inicial, pero también disponible en este servicio si fuera necesario reprocesar.

```python
minio_client.upload_bytes("docs/contrato.pdf", file_bytes, "application/pdf")
```

---

## 8. Embeddings vectoriales

`app/embeddings.py` gestiona el modelo `all-MiniLM-L6-v2` de SentenceTransformers como singleton en memoria.

### El modelo

`all-MiniLM-L6-v2` es un modelo compacto (22M parámetros) que produce vectores de **384 dimensiones** con alta calidad semántica para búsqueda. Es ideal para el MVP por su balance velocidad/calidad y porque corre en CPU sin necesidad de GPU.

### Funciones

**`init_model(model_name)`** — carga el modelo a RAM durante el startup. La carga tarda unos segundos; por eso se hace en el lifespan y no en cada request.

**`get_embedding(text)`** — genera el vector para un texto único. Usado en la herramienta `search_documents` para transformar la pregunta del usuario en un vector antes de buscar.

**`get_embeddings_batch(texts)`** — procesa una lista de textos en lotes de 32. Mucho más eficiente que llamar `get_embedding` en un loop, porque el modelo procesa los lotes en paralelo internamente.

**`embedding_to_pg_str(embedding)`** — convierte la lista de floats a un string con formato `[0.12345678,...]` que pgvector acepta en queries SQL. Esta conversión es necesaria porque psycopg2 no serializa listas Python como vectores pgvector automáticamente.

---

## 9. Routers y endpoints

### 9.1 Router de documentos (`/documents`)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/documents/register` | Registra un documento nuevo con status `PROCESSING` |
| `POST` | `/documents/process` | Lanza el pipeline de ingestión en background |
| `GET` | `/documents/` | Lista todos los documentos con su status |
| `GET` | `/documents/{document_id}` | Detalle de un documento específico |
| `DELETE` | `/documents/{document_id}` | Elimina documento y sus chunks (CASCADE) |

#### Flujo coordinado entre NestJS y FastAPI

El proceso de subida de un documento involucra dos servicios:

```
Usuario → NestJS → MinIO (sube PDF)
       → NestJS → POST /documents/register (crea registro en DB)
       → NestJS → POST /documents/process  (lanza pipeline)
       ← FastAPI procesa en background
```

El endpoint `/process` usa `BackgroundTasks` de FastAPI para devolver la respuesta `202 Accepted` inmediatamente y procesar el PDF de forma asíncrona, sin bloquear el request.

```python
@router.post("/process")
def trigger_processing(req: ProcessRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_document, req.document_id)
    return {"message": "Procesamiento iniciado", "document_id": req.document_id}
```

#### Eliminación en cascada

Al eliminar un documento, los chunks asociados se eliminan automáticamente por la constraint `ON DELETE CASCADE` definida en el esquema de PostgreSQL. El endpoint no necesita lógica adicional para esto.

---

### 9.2 Router del agente (`/agent`)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/agent/chat` | Envía una pregunta al agente y recibe respuesta |
| `GET` | `/agent/history/{user_id}` | Historial de conversación de un usuario |

#### Modelo de request/response

```python
class ChatRequest(BaseModel):
    question: str
    user_id: int
    thread_id: str | None = None  # Si None, se usa "user-{user_id}"

class ChatResponse(BaseModel):
    answer: str
    thread_id: str
```

El `thread_id` es el identificador de la conversación para el checkpointer de LangGraph. Si el frontend no lo envía, se genera automáticamente. Enviarlo en requests sucesivos permite continuar la misma conversación con memoria de los intercambios anteriores.

---

## 10. Servicios

### 10.1 Servicio de ingestión (`services/ingestion.py`)

El pipeline completo de procesamiento de documentos:

```
MinIO (PDF bytes)
    ↓
Docling (extracción de texto → Markdown)
    ↓
RecursiveCharacterTextSplitter (chunks de 1000 chars, 100 overlap)
    ↓
SentenceTransformers (embeddings batch de 384 dims)
    ↓
PostgreSQL pgvector (tabla document_chunks)
    ↓
Actualización de status del documento → "READY"
```

#### Función principal

```python
def process_document(document_id: str) -> None:
    _set_document_status(document_id, "PROCESSING")
    minio_path = _get_minio_path(document_id)
    pdf_bytes = minio_client.download_to_bytes(minio_path)
    text = _extract_text(pdf_bytes)        # Docling
    chunks = _splitter.split_text(text)    # Chunking
    embeddings = emb_service.get_embeddings_batch(chunks)
    _store_chunks(document_id, chunks, embeddings)
    _set_document_status(document_id, "READY")
```

En caso de error en cualquier paso, el status queda en `"ERROR"` y la excepción se loggea.

#### Extracción de texto con Docling

Docling trabaja con archivos en disco, no con bytes en memoria. Por eso `_extract_text` usa un archivo temporal:

```python
def _extract_text(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = _converter.convert(source=tmp_path)
        return result.document.export_to_markdown()
    finally:
        os.unlink(tmp_path)  # elimina el archivo aunque falle la conversión
```

Docling exporta el texto como Markdown, preservando la estructura del documento (títulos, listas, tablas), lo que mejora la calidad de los chunks y de las respuestas del agente.

#### Parámetros del splitter

```python
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""],
)
```

- `chunk_size=1000`: cada chunk tiene hasta 1000 caracteres.
- `chunk_overlap=100`: 10% de overlap entre chunks contiguos para que el contexto no se corte abruptamente en los bordes.
- `separators`: el splitter intenta cortar en estos separadores en orden de preferencia (párrafo > línea > oración > espacio > forzado).

#### Almacenamiento en pgvector

Antes de insertar los nuevos chunks, se eliminan los existentes para el mismo documento. Esto permite reprocesar documentos sin duplicar datos.

```python
cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))
for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
    emb_str = emb_service.embedding_to_pg_str(embedding)
    cur.execute(
        "INSERT INTO document_chunks (document_id, content, embedding, chunk_index) VALUES (%s, %s, %s::vector, %s)",
        (document_id, chunk, emb_str, idx),
    )
conn.commit()
```

---

### 10.2 Servicio del agente (`services/agent_service.py`)

#### Arquitectura del agente

El agente usa el patrón **ReAct** (Reasoning + Acting) implementado por LangGraph. En cada turno:

1. El LLM recibe la pregunta y el historial.
2. Decide qué herramienta invocar (o responder directamente).
3. Ejecuta la herramienta y recibe el resultado.
4. Repite hasta que tiene suficiente información para responder.
5. Genera la respuesta final.

```python
_agent = create_react_agent(
    model=llm,          # ChatGroq (llama-3.1-8b-instant)
    tools=ALL_TOOLS,    # 6 herramientas HRMS
    checkpointer=_checkpointer,  # MemorySaver (memoria en RAM)
)
```

#### Memoria de conversación

`MemorySaver` persiste el estado de cada conversación en RAM, indexado por `thread_id`. Esto permite al agente recordar el contexto de intercambios anteriores dentro de la misma sesión. **Nota:** la memoria se pierde al reiniciar el servicio. El historial permanente está en la tabla `chat_history` de PostgreSQL.

#### System prompt

El prompt tiene fecha dinámica inyectada en cada request:

```python
SYSTEM_PROMPT = """Eres Kuaai, el asistente inteligente de RRHH.
Hoy es {today}. Usa esta fecha como referencia cuando el usuario diga
"hoy", "este mes" o "el mes actual".
...
"""

system = SYSTEM_PROMPT.format(today=date.today().isoformat(), year=date.today().year)
```

El prompt instruye al agente sobre:
- Cuándo usar cada herramienta disponible.
- Formato de respuesta (siempre en español, listas para datos de empleados).
- No inventar datos: solo informar lo que devuelvan las herramientas.
- Cómo encadenar herramientas (buscar ID con `get_employee_info` antes de llamar `get_employee_attendance`).

#### Límite de recursión

```python
config = {
    "configurable": {"thread_id": thread_id},
    "recursion_limit": 25,
}
```

El `recursion_limit` evita loops infinitos: si el agente no llega a una respuesta en 25 pasos (herramienta → resultado → herramienta → ...), LangGraph lanza una excepción que el router convierte en `HTTP 500`. Cada ciclo think→act consume 2 nodos en el grafo, por lo que el límite real de herramientas encadenables es ~12.

#### Persistencia del historial

Después de cada intercambio, tanto la pregunta como la respuesta se guardan en `chat_history`:

```python
def _save_history(user_id: int, question: str, answer: str) -> None:
    cur.execute("INSERT INTO chat_history ... VALUES (%s, %s, %s)", (user_id, "user", question))
    cur.execute("INSERT INTO chat_history ... VALUES (%s, %s, %s)", (user_id, "assistant", answer))
    conn.commit()
```

---

## 11. Herramientas del agente IA

Las herramientas de un único parámetro string usan el decorator `@tool` de LangChain. Las herramientas con múltiples parámetros enteros (`get_employee_attendance`, `get_tardiness_report`, `get_monthly_summary`) usan `StructuredTool.from_function()` con un `BaseModel` de Pydantic como `args_schema`, ya que `@tool` no genera schemas JSON correctos para esos casos con `langchain-groq`. El LLM decide cuál invocar leyendo sus docstrings; por eso están redactados en lenguaje natural sin secciones `Args:` estructuradas (que malforman el schema).

### Herramientas disponibles

#### `search_documents(query: str)`

Búsqueda semántica en los documentos empresariales cargados. Convierte la query en un embedding y busca los 4 chunks más similares usando distancia coseno en pgvector.

```sql
SELECT dc.content, d.name, ROUND((1 - (dc.embedding <=> %s::vector))::numeric, 3) AS similarity
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE d.status = 'READY'
ORDER BY dc.embedding <=> %s::vector
LIMIT 4
```

El operador `<=>` es la distancia coseno de pgvector. El índice `ivfflat` en la columna `embedding` acelera esta búsqueda enormemente para grandes volúmenes de chunks.

---

#### `get_daily_attendance(date: str)`

Asistencia del día (quiénes vinieron, tardanzas, hora de entrada). Filtra por `record_type = 'ENTRADA'` y cruza con el total de empleados activos para calcular ausentes.

**Retorna:**
```json
{
  "fecha": "2024-11-15",
  "total_activos": 42,
  "presentes": 38,
  "ausentes": 4,
  "tardanzas": 3,
  "detalle": [...]
}
```

---

#### `get_employee_attendance(employee_id, month, year)`

Historial mensual de asistencia de un empleado específico. Para obtener el `employee_id` numérico, el agente debe primero invocar `get_employee_info`. El system prompt instruve este encadenamiento.

---

#### `get_tardiness_report(month, year)`

Ranking de empleados con tardanzas en el mes, ordenados de mayor a menor cantidad. Agrupa por empleado con `COUNT(*)` sobre registros donde `is_late = true`.

---

#### `get_monthly_summary(month, year)`

Resumen ejecutivo del mes: porcentaje de asistencia promedio, total de tardanzas, detalle día a día.

```python
avg_pct = round((avg_present / total_active * 100), 1)
```

---

#### `get_employee_info(query: str)`

Búsqueda de empleados por nombre, apellido o legajo con `ILIKE` (case-insensitive). Diseñada para ser el primer paso antes de consultar datos de asistencia cuando el usuario menciona a alguien por nombre.

```sql
WHERE first_name ILIKE %s OR last_name ILIKE %s
   OR (first_name || ' ' || last_name) ILIKE %s
   OR legajo ILIKE %s
```

---

### Lista `ALL_TOOLS`

```python
ALL_TOOLS = [
    search_documents,
    get_daily_attendance,
    get_employee_attendance,
    get_tardiness_report,
    get_monthly_summary,
    get_employee_info,
]
```

Esta lista se pasa directamente a `create_react_agent`. El agente infiere el uso de cada herramienta de sus docstrings y de las instrucciones del system prompt.

---

## 12. Esquema de base de datos

El esquema completo está en `infra/postgres/init.sql`. Las tablas relevantes para este servicio:

### `documents`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK generado automáticamente |
| `name` | VARCHAR(255) | Nombre del archivo |
| `minio_path` | VARCHAR(500) | Ruta en MinIO para descargar el PDF |
| `status` | VARCHAR(20) | `PROCESSING` / `READY` / `ERROR` |
| `uploaded_by` | INTEGER | FK a `users.id` |
| `created_at` | TIMESTAMP | Fecha de registro |

---

### `document_chunks`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | SERIAL | PK autoincremental |
| `document_id` | UUID | FK a `documents.id` (CASCADE DELETE) |
| `content` | TEXT | Texto del chunk |
| `embedding` | vector(384) | Vector semántico del chunk |
| `chunk_index` | INTEGER | Posición del chunk en el documento |

El índice `ivfflat` sobre `embedding` con `lists = 100` optimiza las búsquedas por coseno. `lists = 100` es adecuado para colecciones de hasta ~1M vectores.

---

### `chat_history`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | SERIAL | PK |
| `user_id` | INTEGER | FK a `users.id` |
| `role` | VARCHAR(20) | `user` o `assistant` |
| `content` | TEXT | Contenido del mensaje |
| `created_at` | TIMESTAMP | Timestamp del mensaje |

---

### `employees` y `attendance_records`

Estas tablas son gestionadas por el backend NestJS. FastAPI las lee pero no las escribe. Las herramientas del agente hacen queries de solo lectura sobre ellas.

---

## 13. Flujos completos

### Flujo 1 — Ingestión de un documento

```
[Usuario sube PDF en el frontend]
        ↓
[NestJS sube PDF a MinIO]
        ↓
[NestJS → POST /documents/register]
  payload: { name, minio_path, uploaded_by }
  resultado: { document_id, status: "PROCESSING" }
        ↓
[NestJS → POST /documents/process]
  payload: { document_id }
  resultado: HTTP 202 inmediato
        ↓
[FastAPI ejecuta en background:]
  1. Descarga PDF de MinIO (bytes)
  2. Escribe archivo temporal en disco
  3. Docling extrae texto → Markdown
  4. Splitter corta en chunks de 1000 chars
  5. SentenceTransformers genera embeddings batch
  6. Inserta chunks + embeddings en document_chunks
  7. Actualiza documents.status = "READY"
        ↓
[El frontend puede consultar GET /documents/{id} para ver el status]
```

---

### Flujo 2 — Consulta al agente RAG

```
[Usuario escribe pregunta en el chat del frontend]
        ↓
[NestJS autentica el request con JWT]
        ↓
[NestJS → POST /agent/chat]
  payload: { question, user_id, thread_id }
        ↓
[agent_service.chat()]
  1. Inyecta fecha de hoy en el system prompt
  2. Invoca _agent.invoke() con messages + config de thread
        ↓
[LangGraph ReAct loop:]
  Paso 1: LLM analiza la pregunta
  Paso 2: Elige herramienta (ej: search_documents)
  Paso 3: Ejecuta herramienta → resultado
  Paso 4: LLM analiza resultado
  Paso 5: Si necesita más info → nueva herramienta
  Paso N: LLM genera respuesta final
        ↓
[Persiste pregunta + respuesta en chat_history]
        ↓
[Retorna { answer, thread_id }]
```

---

### Flujo 3 — Búsqueda semántica dentro de `search_documents`

```
query = "¿cuáles son los días de vacaciones según convenio?"
        ↓
embedding = SentenceTransformers.encode(query)  # vector[384]
        ↓
SQL: SELECT content, document_name, similarity
     FROM document_chunks
     ORDER BY embedding <=> query_vector   ← distancia coseno pgvector
     LIMIT 4
        ↓
Retorna los 4 fragmentos más relevantes al LLM
        ↓
LLM sintetiza la respuesta citando la información de los fragmentos
```

---

## 14. Docker

El Dockerfile tiene dos stages: `development` y `production`.

### Stage development

```dockerfile
FROM base AS development
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

`--reload` recarga automáticamente la app cuando cambia el código. Solo para desarrollo local.

### Stage production

```dockerfile
FROM base AS production
COPY . .
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

El `RUN` pre-descarga el modelo de embeddings en tiempo de build para que no dependa de conexión a internet en runtime. Con `--workers 2` se lanzan dos procesos Uvicorn; cada uno inicializa su propio pool de DB y su propia instancia del modelo en memoria.

### Dependencias del sistema

```dockerfile
RUN apt-get install -y libpq-dev gcc g++ libgl1 libglib2.0-0
```

- `libpq-dev`, `gcc`: para compilar psycopg2.
- `g++`, `libgl1`, `libglib2.0-0`: requeridas por Docling para procesar PDFs.

---

## 15. Variables de entorno

| Variable | Default | Obligatoria | Descripción |
|---|---|---|---|
| `POSTGRES_HOST` | `postgres` | No | Host del servidor PostgreSQL |
| `POSTGRES_PORT` | `5432` | No | Puerto PostgreSQL |
| `POSTGRES_DB` | `kuaai` | No | Nombre de la base de datos |
| `POSTGRES_USER` | `kuaai_user` | No | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | `kuaai_password` | No | Contraseña PostgreSQL |
| `MINIO_ENDPOINT` | `minio` | No | Host de MinIO |
| `MINIO_PORT` | `9000` | No | Puerto MinIO |
| `MINIO_ACCESS_KEY` | `kuaai_access` | No | Access key MinIO |
| `MINIO_SECRET_KEY` | `kuaai_secret` | No | Secret key MinIO |
| `MINIO_BUCKET_DOCUMENTS` | `documents` | No | Bucket para documentos PDF |
| `GROQ_API_KEY` | — | **Sí** | API key de Groq |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | No | Modelo Groq a usar |
| `EMBEDDINGS_MODEL` | `all-MiniLM-L6-v2` | No | Modelo SentenceTransformers |
| `EMBEDDINGS_DIMENSIONS` | `384` | No | Dimensiones del vector |
| `FASTAPI_PORT` | `8000` | No | Puerto de escucha |

Los valores default corresponden a la configuración del `docker-compose.yml` del monorepo. En producción se deben sobreescribir con valores reales, especialmente las credenciales.
