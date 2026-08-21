# FastAPI API Reference

## Base URL

```
http://localhost:8000
```

En producción (Docker): `http://backend-fastapi:8000` (red interna Docker).

**Documentación interactiva (Swagger UI):**
```
http://localhost:8000/docs
```

**OpenAPI JSON:**
```
http://localhost:8000/openapi.json
```

---

## Endpoints de Documents

### `POST /documents/upload`

Recibe un PDF desde el frontend (multipart/form-data), lo sube a MinIO y registra el documento en la base de datos con estado `PROCESSING`. Es el punto de entrada principal del flujo de carga de documentos desde la UI.

**Form data:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `file` | `UploadFile` | Archivo PDF (validado por extensión `.pdf` y contenido no vacío) |
| `uploaded_by` | `int` | ID del usuario autenticado |

**Almacenamiento en MinIO:** `{document_id}/{filename_safe}` (los espacios del nombre se reemplazan con `_`).

**Respuesta `200`:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Respuesta `400` — archivo no PDF:**
```json
{ "detail": "Solo se permiten archivos PDF" }
```

**Respuesta `400` — archivo vacío:**
```json
{ "detail": "El archivo está vacío" }
```

**curl:**
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/ruta/al/Reglamento_Interno.pdf" \
  -F "uploaded_by=1"
```

**Flujo completo desde la UI:**
```bash
# 1. Subir el PDF
RESPONSE=$(curl -s -X POST http://localhost:8000/documents/upload \
  -F "file=@Reglamento_Interno.pdf" \
  -F "uploaded_by=1")

DOC_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['document_id'])")

# 2. Disparar el pipeline de ingestión
curl -X POST http://localhost:8000/documents/process \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$DOC_ID\"}"

# 3. Verificar estado (esperar ~10-60 segundos)
curl http://localhost:8000/documents/$DOC_ID
```

---

### `POST /documents/register`

Registra un nuevo documento en la base de datos con estado `PROCESSING`. Normalmente llamado por NestJS después de subir el PDF a MinIO.

**Body:**
```json
{
  "name": "Reglamento Interno 2026.pdf",
  "minio_path": "reglamento-interno-2026.pdf",
  "uploaded_by": 1
}
```

**Respuesta `200`:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING"
}
```

**curl:**
```bash
curl -X POST http://localhost:8000/documents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Reglamento Interno 2026.pdf",
    "minio_path": "reglamento-interno-2026.pdf",
    "uploaded_by": 1
  }'
```

---

### `POST /documents/process`

Dispara el pipeline de ingestión en background para el documento indicado.

**Secuencia del pipeline (asincrónico):**
1. Descarga el PDF desde MinIO usando `minio_path`
2. Extrae el texto con Docling
3. Divide en chunks (500 chars / 50 overlap)
4. Genera embeddings con SentenceTransformers (384 dims)
5. Almacena chunks en `document_chunks` (pgvector)
6. Actualiza `documents.status` a `READY` (o `ERROR` si falla)

**Body:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Respuesta `200` (inmediata, el procesamiento continúa en background):**
```json
{
  "message": "Procesamiento iniciado",
  "document_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**curl:**
```bash
curl -X POST http://localhost:8000/documents/process \
  -H "Content-Type: application/json" \
  -d '{"document_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Flujo completo de subida y procesamiento:**
```bash
# 1. Registrar el documento
RESPONSE=$(curl -s -X POST http://localhost:8000/documents/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Politicas de RRHH.pdf","minio_path":"politicas-rrhh.pdf","uploaded_by":1}')

DOC_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['document_id'])")

# 2. Disparar el pipeline
curl -X POST http://localhost:8000/documents/process \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$DOC_ID\"}"

# 3. Verificar estado (esperar ~10-30 segundos según tamaño del PDF)
sleep 15
curl http://localhost:8000/documents/$DOC_ID
```

---

### `GET /documents/`

Lista todos los documentos con su estado actual.

**Respuesta `200`:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Reglamento Interno 2026.pdf",
    "status": "READY",
    "created_at": "2026-05-11T10:30:00"
  },
  {
    "id": "661f9511-f30c-52e5-b827-557766551111",
    "name": "Manual de Procedimientos.pdf",
    "status": "PROCESSING",
    "created_at": "2026-05-11T11:00:00"
  }
]
```

**curl:**
```bash
curl http://localhost:8000/documents/
```

---

### `GET /documents/{document_id}`

Retorna el detalle de un documento específico.

**Respuesta `200`:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Reglamento Interno 2026.pdf",
  "minio_path": "reglamento-interno-2026.pdf",
  "status": "READY",
  "created_at": "2026-05-11T10:30:00"
}
```

**Respuesta `404`:**
```json
{ "detail": "Documento no encontrado" }
```

**curl:**
```bash
curl http://localhost:8000/documents/550e8400-e29b-41d4-a716-446655440000
```

---

### `GET /documents/{document_id}/download`

Descarga el archivo PDF original desde MinIO (usado por el visor de PDF del frontend, vía proxy NestJS).

**Respuesta `200`:** el binario del PDF con `Content-Type: application/pdf`.

**curl:**
```bash
curl http://localhost:8000/documents/550e8400-e29b-41d4-a716-446655440000/download -o documento.pdf
```

---

### `GET /documents/{document_id}/chunks`

Lista todos los chunks de un documento con métricas de su embedding (norma, sparsity, muestra de valores). Usado por el panel de administración (`/admin/chunks`).

**Respuesta `200`:**
```json
[
  {
    "id": 1,
    "chunk_index": 0,
    "content": "Los empleados tienen derecho a...",
    "char_count": 412,
    "estimated_tokens": 103,
    "embedding": {
      "dims": 384,
      "norm": 1.0,
      "max": 0.187432,
      "min": -0.163021,
      "sparsity": 0.0234,
      "sample": [0.021, -0.045, 0.102, "..."]
    },
    "created_at": "2026-08-20T21:04:11"
  }
]
```

**Respuesta `404`:** `{ "detail": "Documento no encontrado" }`

**curl:**
```bash
curl http://localhost:8000/documents/550e8400-e29b-41d4-a716-446655440000/chunks
```

---

### `POST /documents/chunks/search`

Búsqueda semántica manual sobre chunks, sin pasar por el agente. Pensado para probar el retrieval directamente desde el panel de administración.

**Body:**
```json
{
  "query": "días de vacaciones",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "limit": 8
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `query` | string | ✅ | Texto a buscar |
| `document_id` | string | — | Si se especifica, limita la búsqueda a ese documento |
| `limit` | integer | — | Cantidad de chunks a retornar (default **8**, distinto del `top_k=4` que usa el agente en `search_documents`) |

**Respuesta `200`:** igual shape que `GET /documents/{id}/chunks`, más `document_id`, `document_name` y `similarity` (float, distancia coseno invertida).

**curl:**
```bash
curl -X POST http://localhost:8000/documents/chunks/search \
  -H "Content-Type: application/json" \
  -d '{"query": "días de vacaciones", "limit": 8}'
```

---

### `DELETE /documents/{document_id}`

Elimina el documento, todos sus chunks (CASCADE) y el archivo original de MinIO.

**Secuencia de eliminación:**
1. Obtiene `minio_path` de la DB
2. Borra el registro de `documents` (los chunks se eliminan en cascada)
3. Elimina el objeto de MinIO (fallo no-fatal: se loguea como warning)

**Respuesta `200`:**
```json
{ "message": "Documento eliminado" }
```

**Respuesta `404`:**
```json
{ "detail": "Documento no encontrado" }
```

**curl:**
```bash
curl -X DELETE http://localhost:8000/documents/550e8400-e29b-41d4-a716-446655440000
```

---

## Endpoints de Agent

### `POST /agent/chat`

Endpoint principal del agente RAG. Recibe la pregunta del usuario, la procesa con el agente LangChain y retorna la respuesta en español.

**Body:**
```json
{
  "question": "¿Quiénes llegaron tarde en mayo de 2026?",
  "user_id": 1,
  "thread_id": "user-1"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `question` | string | ✅ | La pregunta en lenguaje natural |
| `user_id` | integer | ✅ | ID del usuario autenticado (para historial) |
| `thread_id` | string | — | ID de hilo de conversación. Si no se envía, se genera como `"user-{user_id}"`. Usar el mismo `thread_id` para mantener contexto conversacional. |

**Respuesta `200`:**
```json
{
  "answer": "En mayo de 2026, los empleados con tardanzas fueron:\n- Pedro Ramírez (Operaciones): 4 tardanzas\n- Ana Fernández (Administración): 2 tardanzas\n- Juan García (Ventas): 1 tardanza",
  "thread_id": "user-1"
}
```

**Respuesta `429` — rate limit de Groq:**
```json
{ "detail": "Límite de solicitudes alcanzado. Esperá unos segundos e intentá de nuevo." }
```

**Respuesta `500`:**
```json
{ "detail": "Error del agente: <descripción del error>" }
```

**Ejemplos de consultas:**
```bash
# Pregunta sobre documentos empresariales
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuál es la política de licencias por enfermedad?",
    "user_id": 1,
    "thread_id": "user-1"
  }'

# Asistencia del día de hoy
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuántos empleados vinieron hoy?",
    "user_id": 1,
    "thread_id": "user-1"
  }'

# Reporte de tardanzas del mes
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Dame el reporte de tardanzas de mayo 2026",
    "user_id": 1,
    "thread_id": "user-1"
  }'

# Información de un empleado
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿En qué departamento trabaja María López?",
    "user_id": 1,
    "thread_id": "user-1"
  }'

# Resumen mensual
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuál fue el porcentaje de asistencia en abril?",
    "user_id": 1,
    "thread_id": "user-1"
  }'

# Consulta de seguimiento (usa el contexto del thread)
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Y en marzo?",
    "user_id": 1,
    "thread_id": "user-1"
  }'
```

---

### `GET /agent/history/{user_id}`

Retorna el historial de conversación de un usuario desde la base de datos, en orden cronológico.

**Query params:**

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `limit` | integer | `50` | Cantidad máxima de mensajes a retornar |
| `thread_id` | string | — | Si se especifica, filtra el historial a ese hilo de conversación |

**Respuesta `200`:**
```json
[
  {
    "role": "user",
    "content": "¿Cuántos empleados vinieron hoy?",
    "created_at": "2026-05-11T14:30:00"
  },
  {
    "role": "assistant",
    "content": "Hoy vinieron 8 de 10 empleados activos (80% de asistencia). Los ausentes son: Pedro Ramírez y Ana Fernández.",
    "created_at": "2026-05-11T14:30:02"
  }
]
```

**curl:**
```bash
# Últimos 50 mensajes
curl http://localhost:8000/agent/history/1

# Últimos 20 mensajes
curl "http://localhost:8000/agent/history/1?limit=20"
```

---

## Endpoints de Threads

Hilos de conversación múltiples por usuario (Sprint 2). No confundir con
`thread_id` de LangGraph/`recursion_limit` del agente — acá `thread_id` es el
`id` (UUID) de una fila de `conversation_threads`.

### `POST /threads/`

Crea un nuevo hilo de conversación.

**Body:**
```json
{
  "user_id": 1,
  "name": "Consultas de vacaciones"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `user_id` | integer | ✅ | ID del usuario dueño del hilo |
| `name` | string | — | Nombre del hilo (default `"Nueva conversación"`) |

**Respuesta `200`:**
```json
{
  "id": "7f3a1b2c-...",
  "user_id": 1,
  "name": "Consultas de vacaciones",
  "created_at": "2026-08-20T21:00:00",
  "last_message_at": "2026-08-20T21:00:00"
}
```

**curl:**
```bash
curl -X POST http://localhost:8000/threads/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "name": "Consultas de vacaciones"}'
```

---

### `GET /threads/{user_id}`

Lista los hilos de un usuario, ordenados por `last_message_at` descendente (los más recientes primero).

**Respuesta `200`:**
```json
[
  { "id": "7f3a1b2c-...", "name": "Consultas de vacaciones", "created_at": "...", "last_message_at": "..." }
]
```

**curl:**
```bash
curl http://localhost:8000/threads/1
```

---

### `PATCH /threads/{thread_id}/rename`

Renombra un hilo.

**Body:**
```json
{ "name": "Nuevo nombre" }
```

**Respuesta `200`:** `{ "id": "...", "name": "Nuevo nombre" }`

**Respuesta `404`:** `{ "detail": "Hilo no encontrado" }`

---

### `DELETE /threads/{thread_id}`

Elimina un hilo. Los mensajes de `chat_history` que lo referencian quedan con `thread_id = NULL` (no se borran).

**Respuesta `200`:** `{ "message": "Hilo eliminado" }`

**Respuesta `404`:** `{ "detail": "Hilo no encontrado" }`

**Limpieza automática:** además del borrado manual, un cron en NestJS
(`CleanupService`, todos los días a las 3AM) borra los hilos con
`last_message_at` de más de 30 días.

---

## Health Check

### `GET /health`

Verifica que el servicio está activo.

**Respuesta `200`:**
```json
{ "status": "ok" }
```

**curl:**
```bash
curl http://localhost:8000/health
```
