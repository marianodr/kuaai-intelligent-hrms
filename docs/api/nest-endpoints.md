# NestJS API Reference

## Base URL

```
http://localhost:3001
```

En producción (Docker): `http://backend-nest:3001` (red interna Docker).

## Autenticación

Todos los endpoints protegidos requieren un token JWT en el header `Authorization`:

```
Authorization: Bearer <access_token>
```

El token se obtiene mediante `POST /auth/login` y expira según `JWT_EXPIRATION` (default: `24h`).

---

## Endpoints de Auth

### `POST /auth/login`

Autentica un usuario y retorna el token JWT.

**Body:**
```json
{
  "email": "admin@kuaai.com",
  "password": "tu_password"
}
```

**Respuesta exitosa `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "admin@kuaai.com",
    "role": "admin"
  }
}
```

**Respuesta error `401`:**
```json
{
  "statusCode": 401,
  "message": "Credenciales inválidas"
}
```

**curl:**
```bash
curl -X POST http://localhost:3001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@kuaai.com","password":"admin123"}'
```

---

### `GET /auth/me`

Retorna los datos del usuario autenticado.

**Headers:** `Authorization: Bearer <token>`

**Respuesta `200`:**
```json
{
  "id": 1,
  "email": "admin@kuaai.com",
  "role": "admin"
}
```

**curl:**
```bash
curl http://localhost:3001/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

### `POST /auth/logout`

Invalida la sesión del lado del cliente. El servidor retorna confirmación (el JWT es stateless; el logout real se implementa eliminando el token en el cliente).

**Headers:** `Authorization: Bearer <token>`

**Respuesta `200`:**
```json
{ "message": "Sesión cerrada" }
```

---

## Endpoints de Employees

### `GET /employees`

Lista empleados con paginación y filtros opcionales.

**Headers:** `Authorization: Bearer <token>`

**Query params:**

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `page` | number | `1` | Página actual |
| `limit` | number | `10` | Items por página |
| `name` | string | — | Filtra por nombre o apellido (ILIKE) |
| `department` | string | — | Filtra por departamento exacto |

**Respuesta `200`:**
```json
{
  "data": [
    {
      "id": 1,
      "first_name": "Juan",
      "last_name": "García",
      "email": "juan@empresa.com",
      "legajo": "EMP-001",
      "rfid_code": "A1B2C3D4",
      "department": "Administración",
      "status": "ACTIVO",
      "created_at": "2026-05-01T10:00:00.000Z"
    }
  ],
  "total": 25,
  "page": 1,
  "limit": 10,
  "totalPages": 3
}
```

**curl:**
```bash
# Lista básica
curl "http://localhost:3001/employees" \
  -H "Authorization: Bearer $TOKEN"

# Con filtros
curl "http://localhost:3001/employees?page=1&limit=5&name=garcia&department=Administración" \
  -H "Authorization: Bearer $TOKEN"
```

---

### `GET /employees/:id`

Retorna el detalle de un empleado.

**curl:**
```bash
curl http://localhost:3001/employees/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

### `POST /employees`

Crea un nuevo empleado.

**Body:**
```json
{
  "first_name": "María",
  "last_name": "López",
  "email": "maria.lopez@empresa.com",
  "legajo": "EMP-002",
  "rfid_code": "F1E2D3C4",
  "department": "Operaciones"
}
```

**Respuesta `201`:** objeto Employee completo.

**Errores comunes:**
- `400` — validación fallida (email inválido, campos faltantes)
- `409` — legajo o rfid_code ya existen

**curl:**
```bash
curl -X POST http://localhost:3001/employees \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "María",
    "last_name": "López",
    "email": "maria.lopez@empresa.com",
    "legajo": "EMP-002",
    "rfid_code": "F1E2D3C4",
    "department": "Operaciones"
  }'
```

---

### `PUT /employees/:id`

Actualiza datos de un empleado. Solo los campos enviados se modifican.

**Body (todos opcionales):**
```json
{
  "department": "Recursos Humanos",
  "email": "nuevo@empresa.com",
  "status": "INACTIVO"
}
```

**curl:**
```bash
curl -X PUT http://localhost:3001/employees/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"department": "Recursos Humanos"}'
```

---

### `DELETE /employees/:id`

Da de baja al empleado (cambia `status` a `INACTIVO`). No elimina el registro ni su historial de asistencias.

**Respuesta `200`:** objeto Employee con `status: "INACTIVO"`.

**curl:**
```bash
curl -X DELETE http://localhost:3001/employees/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Endpoints de Dashboard

### `GET /dashboard/today`

Retorna la asistencia del día actual: presentes, ausentes y lista de ausentes.

**Headers:** `Authorization: Bearer <token>`

**Respuesta `200`:**
```json
{
  "date": "2026-05-11",
  "total_active": 10,
  "present": 8,
  "absent": 2,
  "attendance_pct": 80,
  "absent_employees": [
    { "id": 3, "name": "Pedro Ramírez", "department": "Operaciones" }
  ]
}
```

**curl:**
```bash
curl http://localhost:3001/dashboard/today \
  -H "Authorization: Bearer $TOKEN"
```

---

### `GET /dashboard/monthly-average`

Porcentaje promedio de asistencia del mes indicado (o el mes actual si no se especifica).

**Query params:** `?month=5&year=2026`

**Respuesta `200`:**
```json
{
  "month": 5,
  "year": 2026,
  "workdays": 20,
  "average_attendance_pct": 85
}
```

**curl:**
```bash
curl "http://localhost:3001/dashboard/monthly-average?month=5&year=2026" \
  -H "Authorization: Bearer $TOKEN"
```

---

### `GET /dashboard/tardiness`

Lista de empleados con tardanzas en el mes, ordenados por cantidad descendente.

**Query params:** `?month=5&year=2026`

**Respuesta `200`:**
```json
{
  "month": 5,
  "year": 2026,
  "tardiness": [
    {
      "employee_id": 4,
      "name": "Ana Fernández",
      "department": "Administración",
      "count": 3
    }
  ]
}
```

**curl:**
```bash
curl "http://localhost:3001/dashboard/tardiness?month=5&year=2026" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Endpoints proxy — Documents y Agent

NestJS actúa como API gateway: autentica con JWT y reenvía la solicitud a FastAPI. El frontend **solo** llama a estos endpoints; no accede a FastAPI directamente.

Variable de entorno requerida en NestJS: `FASTAPI_URL=http://backend-fastapi:8000`.

### `POST /documents/upload`

Sube un PDF a FastAPI (que lo almacena en MinIO y registra en DB).

**Headers:** `Authorization: Bearer <token>`  
**Form data:** `file` (PDF), `uploaded_by` (integer)

**Respuesta `200`:** `{ "document_id": "uuid" }`

```bash
curl -X POST http://localhost:3001/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@Reglamento.pdf" \
  -F "uploaded_by=1"
```

---

### `POST /documents/process`

Dispara el pipeline de ingestión RAG en FastAPI (background task).

**Headers:** `Authorization: Bearer <token>`  
**Body:** `{ "document_id": "uuid" }`

**Respuesta `200`:** `{ "message": "Procesamiento iniciado", "document_id": "uuid" }`

---

### `GET /documents`

Lista todos los documentos con su estado.

**Headers:** `Authorization: Bearer <token>`

**Respuesta `200`:** array de documentos `[{ id, name, status, progress, created_at }]`

---

### `GET /documents/:id`

Detalle de un documento.

---

### `DELETE /documents/:id`

Elimina documento, chunks y archivo de MinIO.

**Respuesta `200`:** `{ "message": "Documento eliminado" }`

---

### `POST /agent/chat`

Envía una pregunta al agente RAG.

**Headers:** `Authorization: Bearer <token>`  
**Body:** `{ "question": string, "user_id": integer, "thread_id"?: string }`

**Respuesta `200`:** `{ "answer": string, "thread_id": string }`  
**Respuesta `429`:** rate limit de Groq superado — reintentar en ~60 segundos.

```bash
curl -X POST http://localhost:3001/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Quiénes llegaron tarde hoy?","user_id":1,"thread_id":"user-1"}'
```

---

### `GET /agent/history/:userId`

Historial de conversación del usuario.

**Headers:** `Authorization: Bearer <token>`  
**Query:** `?limit=50`

**Respuesta `200`:** array `[{ role, content, created_at }]`

---

## Códigos de error comunes

| Código | Significado | Causa típica |
|--------|-------------|--------------|
| `400` | Bad Request | Validación de DTO fallida (campo faltante, formato inválido) |
| `401` | Unauthorized | Token JWT ausente, expirado o inválido |
| `403` | Forbidden | El rol del usuario no tiene permiso para esa acción |
| `404` | Not Found | Empleado u recurso no encontrado |
| `409` | Conflict | Email, legajo o rfid_code duplicado |
| `500` | Internal Server Error | Error inesperado del servidor |
