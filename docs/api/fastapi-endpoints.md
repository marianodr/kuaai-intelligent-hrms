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
3. Divide en chunks (1000 chars / 100 overlap)
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

### `DELETE /documents/{document_id}`

Elimina el documento y todos sus chunks (CASCADE). El archivo en MinIO **no** se elimina automáticamente.

**Respuesta `200`:**
```json
{ "message": "Documento eliminado" }
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
