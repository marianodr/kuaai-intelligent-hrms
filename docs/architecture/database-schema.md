# Database Schema

## Diagrama ER

```mermaid
erDiagram
    users {
        serial id PK
        varchar email UK
        varchar password
        varchar role "admin | rrhh"
        boolean is_active
        timestamp created_at
    }

    employees {
        serial id PK
        varchar first_name
        varchar last_name
        varchar email UK
        varchar legajo UK
        varchar rfid_code UK
        varchar department
        varchar status "ACTIVO | INACTIVO"
        timestamp created_at
        timestamp updated_at
    }

    attendance_records {
        serial id PK
        integer employee_id FK
        timestamp timestamp
        varchar record_type "ENTRADA | SALIDA | INTERMEDIO"
        boolean is_late
        boolean auto_generated
        timestamp created_at
    }

    documents {
        uuid id PK
        varchar name
        varchar minio_path
        varchar status "PROCESSING | READY | ERROR"
        varchar progress "descripción del paso actual"
        integer uploaded_by FK
        timestamp created_at
    }

    document_chunks {
        serial id PK
        uuid document_id FK
        text content
        vector embedding "384 dims"
        integer chunk_index
        timestamp created_at
    }

    chat_history {
        serial id PK
        integer user_id FK
        varchar role "user | assistant"
        text content
        uuid thread_id FK "nullable"
        timestamp created_at
    }

    conversation_threads {
        uuid id PK
        integer user_id FK
        varchar name "default 'Nueva conversación'"
        timestamp created_at
        timestamp last_message_at
    }

    system_logs {
        bigserial id PK
        varchar level "INFO | WARN | ERROR"
        varchar service "nest | fastapi"
        varchar event
        integer user_id FK "nullable"
        jsonb detail
        timestamp created_at
    }

    employees ||--o{ attendance_records : "tiene"
    users ||--o{ documents : "sube"
    documents ||--o{ document_chunks : "tiene"
    users ||--o{ chat_history : "genera"
    users ||--o{ conversation_threads : "tiene"
    conversation_threads ||--o{ chat_history : "agrupa"
    users ||--o{ system_logs : "genera (opcional)"
```

---

## Descripción de cada tabla

### `users`
Usuarios del sistema con acceso al panel web. Solo existen dos roles.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL PK` | Identificador autoincremental |
| `email` | `VARCHAR(255) UNIQUE` | Email de login (único) |
| `password` | `VARCHAR(255)` | Hash bcrypt (saltRounds=10) |
| `role` | `VARCHAR(50)` | `admin` o `rrhh`. Check constraint. |
| `is_active` | `BOOLEAN` | Permite desactivar un usuario sin eliminarlo |
| `created_at` | `TIMESTAMP` | Fecha de creación (DEFAULT NOW()) |

---

### `employees`
Empleados de la empresa. El `rfid_code` vincula al empleado con su tarjeta física.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL PK` | Identificador autoincremental |
| `first_name` | `VARCHAR(100)` | Nombre |
| `last_name` | `VARCHAR(100)` | Apellido |
| `email` | `VARCHAR(255) UNIQUE` | Email del empleado (nullable) |
| `legajo` | `VARCHAR(50) UNIQUE` | Número de legajo interno (único) |
| `rfid_code` | `VARCHAR(100) UNIQUE` | UID de la tarjeta RFID (único) |
| `department` | `VARCHAR(100)` | Departamento (nullable) |
| `status` | `VARCHAR(20)` | `ACTIVO` o `INACTIVO`. Check constraint. |
| `created_at` | `TIMESTAMP` | Fecha de alta |
| `updated_at` | `TIMESTAMP` | Actualizado automáticamente por trigger |

**Nota:** los empleados dados de baja conservan `status = 'INACTIVO'` para preservar el historial de asistencias. No se eliminan físicamente.

---

### `attendance_records`
Registro de cada marcación de tarjeta RFID. Un empleado puede tener múltiples registros por día.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL PK` | Identificador autoincremental |
| `employee_id` | `INTEGER FK` | Referencia a `employees.id` |
| `timestamp` | `TIMESTAMP` | Fecha y hora exacta del evento |
| `record_type` | `VARCHAR(20)` | `ENTRADA`, `SALIDA` o `INTERMEDIO` |
| `is_late` | `BOOLEAN` | `true` si la ENTRADA fue después de las 08:05 (tolerancia configurable vía `LATE_TOLERANCE_MINUTES`) |
| `auto_generated` | `BOOLEAN` | `true` si fue generado por el cron de las 16:00 |
| `created_at` | `TIMESTAMP` | Fecha de inserción en DB |

**Lógica de record_type:**
- Primer registro del día → `ENTRADA`
- Segundo registro del día → `SALIDA`
- Tercero en adelante → `INTERMEDIO`

---

### `documents`
Metadatos de los documentos PDF subidos por los usuarios. El archivo físico está en MinIO.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `UUID PK` | Identificador UUID generado por `gen_random_uuid()` |
| `name` | `VARCHAR(255)` | Nombre original del archivo |
| `minio_path` | `VARCHAR(500)` | Path dentro del bucket MinIO |
| `status` | `VARCHAR(20)` | `PROCESSING`, `READY` o `ERROR` |
| `progress` | `VARCHAR(100)` | Descripción del paso actual del pipeline (nullable). Ej: `"Extrayendo texto..."`. Añadida por migración `001_add_document_progress.sql` |
| `uploaded_by` | `INTEGER FK` | Referencia a `users.id` (nullable) |
| `created_at` | `TIMESTAMP` | Fecha de subida |

---

### `document_chunks`
Fragmentos de texto de los documentos con sus embeddings vectoriales. Es la tabla central del sistema RAG.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL PK` | Identificador autoincremental |
| `document_id` | `UUID FK` | Referencia a `documents.id` (ON DELETE CASCADE) |
| `content` | `TEXT` | Texto del fragmento (hasta ~500 caracteres) |
| `embedding` | `vector(384)` | Embedding generado por `paraphrase-multilingual-MiniLM-L12-v2` |
| `chunk_index` | `INTEGER` | Posición del chunk dentro del documento (0-based) |
| `created_at` | `TIMESTAMP` | Fecha de inserción |

**Búsqueda por similitud coseno:**
```sql
SELECT content, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM document_chunks
WHERE document_id IN (SELECT id FROM documents WHERE status = 'READY')
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 4;
```

---

### `chat_history`
Historial de conversaciones entre usuarios y el agente RAG. Cada par pregunta/respuesta genera dos filas.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL PK` | Identificador autoincremental |
| `user_id` | `INTEGER FK` | Referencia a `users.id` (nullable) |
| `role` | `VARCHAR(20)` | `user` o `assistant` |
| `content` | `TEXT` | Texto del mensaje |
| `thread_id` | `UUID FK` | Referencia a `conversation_threads.id` (nullable, `ON DELETE SET NULL`). Añadida por migración `002_conversation_threads.sql` |
| `created_at` | `TIMESTAMP` | Timestamp del mensaje |

---

### `conversation_threads`
Hilos de conversación del agente RAG — permite que un usuario tenga varias
conversaciones separadas en paralelo (panel lateral en la página de chat del
frontend). Agregada por migración `002_conversation_threads.sql` (Sprint 2).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `UUID PK` | Identificador generado por `gen_random_uuid()` |
| `user_id` | `INTEGER FK` | Referencia a `users.id` (`ON DELETE CASCADE`) |
| `name` | `VARCHAR(255)` | Nombre del hilo (default `'Nueva conversación'`) |
| `created_at` | `TIMESTAMP` | Fecha de creación |
| `last_message_at` | `TIMESTAMP` | Actualizado en cada mensaje (usado para el TTL de limpieza) |

**Limpieza automática:** un cron en NestJS (`CleanupService`,
`@Cron(EVERY_DAY_AT_3AM)`) borra los hilos con `last_message_at` de más de
30 días (valor hardcodeado, no configurable por env var).

---

### `system_logs`
Tabla de auditoría agregada por migración `003_system_logs.sql` (Sprint 3).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `BIGSERIAL PK` | Identificador autoincremental |
| `level` | `VARCHAR(10)` | `INFO`, `WARN` o `ERROR`. Check constraint |
| `service` | `VARCHAR(20)` | `nest` o `fastapi`. Check constraint |
| `event` | `VARCHAR(100)` | Nombre del evento loggeado |
| `user_id` | `INTEGER FK` | Referencia a `users.id` (nullable, `ON DELETE SET NULL`) |
| `detail` | `JSONB` | Detalle estructurado del evento |
| `created_at` | `TIMESTAMP` | Timestamp del evento |

**⚠️ Tabla actualmente sin uso real:** ni `AuditLogMiddleware` (FastAPI,
`app/middleware/audit_log.py`) ni `LoggingInterceptor` (NestJS,
`src/logging/logging.interceptor.ts`) insertan filas acá — ambos solo
loguean a stdout/archivo. El schema existe pero no hay código que lo pueble.

---

## Índices y extensiones

### Extensiones PostgreSQL

```sql
CREATE EXTENSION IF NOT EXISTS vector;       -- pgvector: tipo vector y operadores <=> <#> <+>
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- gen_random_uuid() para documents.id
```

### Índices de búsqueda vectorial

```sql
-- Índice IVFFlat para búsqueda aproximada por distancia coseno
-- lists=100 es apropiado para colecciones de hasta ~1M vectores
CREATE INDEX ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Índices de acceso frecuente

```sql
-- Consultas de asistencia por empleado y por fecha (muy frecuentes)
CREATE INDEX idx_attendance_employee_id ON attendance_records(employee_id);
CREATE INDEX idx_attendance_timestamp ON attendance_records(timestamp);

-- Acceso a chunks por documento (para eliminación en cascade y reproceso)
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);

-- Historial de chat por usuario
CREATE INDEX idx_chat_history_user_id ON chat_history(user_id);

-- Hilos de conversación: listado por usuario y limpieza por antigüedad
CREATE INDEX idx_threads_user_id ON conversation_threads(user_id);
CREATE INDEX idx_threads_last_message ON conversation_threads(last_message_at);

-- Historial de chat por hilo
CREATE INDEX idx_chat_history_thread_id ON chat_history(thread_id);

-- Logs de sistema: filtrado por fecha, nivel y evento
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_event ON system_logs(event);
```

### Trigger de updated_at

```sql
-- Actualiza employees.updated_at automáticamente en cada UPDATE
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER employees_updated_at
  BEFORE UPDATE ON employees
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

---

## Relaciones entre tablas

| Tabla origen | Columna | Tabla destino | Tipo | Comportamiento |
|---|---|---|---|---|
| `attendance_records` | `employee_id` | `employees.id` | FK | RESTRICT (no elimina empleados con registros) |
| `documents` | `uploaded_by` | `users.id` | FK | nullable |
| `document_chunks` | `document_id` | `documents.id` | FK | **ON DELETE CASCADE** (eliminar doc borra sus chunks) |
| `chat_history` | `user_id` | `users.id` | FK | nullable |
| `chat_history` | `thread_id` | `conversation_threads.id` | FK | nullable, **ON DELETE SET NULL** |
| `conversation_threads` | `user_id` | `users.id` | FK | **ON DELETE CASCADE** |
| `system_logs` | `user_id` | `users.id` | FK | nullable, **ON DELETE SET NULL** |
