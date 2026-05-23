# PLAN.md — Kuaai: Intelligent HRMS

## 1. Descripción del producto

Kuaai es un MVP de Sistema de Gestión de Recursos Humanos (HRMS) inteligente
orientado a PyMEs de la región de Misiones, Argentina. Combina control de
asistencias mediante IoT, gestión de empleados y un agente RAG que permite
realizar consultas en lenguaje natural sobre documentos empresariales y datos
estructurados.

**Nombre:** Kuaai (del guaraní "kuaa": saber, conocimiento)
**Tipo:** MVP académico — Proyecto Final de Grado
**Universidad:** Universidad Nacional de Misiones (UNaM)
**Autor:** Mariano David Rodriguez

---

## 2. Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend principal | NestJS (TypeScript) |
| Backend IA | FastAPI (Python) |
| Frontend | Next.js 14+ + TypeScript + Tailwind CSS + shadcn/ui |
| Base de datos | PostgreSQL + pgvector |
| Object storage | MinIO |
| Mensajería IoT | MQTT + Mosquitto |
| Agente LLM | LangChain + Groq (Llama 3.1 8B) |
| Ingestión documentos | Docling + SentenceTransformers |
| Autenticación | JWT con roles |
| IoT | Raspberry Pi Pico 2W + RFID RC522 + MicroPython |
| Contenedorización | Docker + Docker Compose |

---

## 3. Estructura del repositorio (Monorepo)

```
kuaai/
├── apps/
│   ├── frontend/           # Next.js
│   ├── backend-nest/       # NestJS — CRUD, MQTT, auth
│   ├── backend-fastapi/    # FastAPI — RAG, agente, embeddings
│   └── iot-node/           # MicroPython — Raspberry Pi Pico 2W
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── PLAN.md
└── README.md
```

---

## 4. Arquitectura del sistema

### Patrón arquitectónico

El sistema combina 3 patrones:

- **Orientada a eventos (Event-Driven):** el nodo IoT publica eventos MQTT que NestJS consume asincrónicamente y persiste en PostgreSQL.
- **Cliente-Servidor (tres capas):** el frontend Next.js consume la API REST de NestJS para gestión de empleados, dashboard y autenticación. Para consultas RAG, Next.js consume la API de FastAPI.
- **Agéntico (Agentic RAG):** El agente LangChain orquesta dinámicamente múltiples herramientas para responder consultas en lenguaje natural, decidiendo en tiempo de ejecución si consultar documentos en pgvector, datos estructurados en PostgreSQL, o ambos simultáneamente.

### Diagrama de servicios

```
[Raspberry Pi Pico 2W]
        |
      MQTT
        |
[Mosquitto Broker]
        |
[NestJS Backend] ←——REST——→ [Next.js Frontend]
        |                          |
        |                    REST (RAG)
        |                          |
   PostgreSQL              [FastAPI Backend]
   + pgvector                      |
        |                   LangChain Agent
      MinIO                        |
                              Groq API
                           (Llama 3.1 8B)
```

### Responsabilidades por servicio

**NestJS:**
- Autenticación JWT y gestión de roles
- CRUD de empleados
- Suscripción MQTT y procesamiento de eventos IoT
- Endpoints del dashboard (métricas de asistencia)
- Proxy de requests al backend FastAPI cuando es necesario

**FastAPI:**
- Pipeline de ingestión de documentos PDF
  (Docling → chunks → SentenceTransformers → pgvector)
- Agente LangChain con herramientas predefinidas
- Endpoints de chat RAG
- Gestión de archivos en MinIO

**Next.js:**
- Interfaz de login
- Dashboard de asistencias
- Gestión de empleados
- Carga de documentos
- Interfaz de chat con el agente

**Mosquitto:**
- Broker MQTT que recibe eventos del nodo IoT
- NestJS se suscribe al topic `attendance/checkin`

**PostgreSQL + pgvector:**
- Datos relacionales: empleados, asistencias, documentos, usuarios
- Vectores: embeddings de chunks de documentos

**MinIO:**
- Almacenamiento de archivos PDF originales

---

## 5. Módulos y responsabilidades

### Módulo 1 — Autenticación y roles

**Roles:**
- **Admin:** crea y gestiona responsables de RRHH, acceso total
- **Responsable de RRHH:** gestiona empleados, documentos y consulta el agente

**Flujo de login:**
1. Usuario ingresa credenciales en Next.js
2. Next.js llama a NestJS `/auth/login`
3. NestJS valida y retorna JWT
4. JWT se almacena en cookie httpOnly
5. Todas las requests siguientes incluyen el JWT

---

### Módulo 2 — Control de asistencias IoT

**Hardware:**
- Microcontrolador: Raspberry Pi Pico 2W
- Lector RFID: RC522
- Firmware: MicroPython

**Flujo de registro:**
1. Empleado acerca tarjeta RFID al lector
2. Pico 2W lee el UID de la tarjeta
3. Publica en MQTT topic `attendance/checkin`:
   ```json
   { "rfid_code": "ABC12345" }
   ```
4. NestJS recibe el evento vía suscripción MQTT
5. Busca el empleado por `rfid_code` en PostgreSQL
6. Determina el tipo de registro según lógica de negocio
7. Persiste el registro en la tabla `attendance_records`
8. Actualiza métricas del dashboard en tiempo real

**Lógica de registros:**

| Registro del día | Tipo asignado |
|---|---|
| Primero | ENTRADA |
| Intermedios | INTERMEDIO |
| Último | SALIDA |

**Lógica de tardanza:**
- Entrada registrada después de las 08:15 → `is_late: true`

**Salida automática:**
- Si a las 16:00 no hay registro de SALIDA →
  se genera automáticamente con `auto_generated: true`
- Un job programado (cron) en NestJS ejecuta esto diariamente a las 16:00

**Horario laboral:**
- Entrada esperada: 08:00
- Salida esperada: 16:00
- Tolerancia para tardanza: 15 minutos

---

### Módulo 3 — Gestión de empleados (CRUD)

**Datos del empleado:**
- id
- nombre
- apellido
- email
- legajo
- rfid_code
- departamento
- estado: ACTIVO | INACTIVO

**Operaciones:**
- Listar empleados (paginado, con filtros por nombre y departamento)
- Crear empleado
- Editar empleado
- Dar de baja (cambia estado a INACTIVO, preserva historial)

---

### Módulo 4 — Agente RAG

**Fuentes de información:**
1. Documentos empresariales (pgvector) — políticas, reglamentos, manuales
2. Datos estructurados (PostgreSQL) — empleados, asistencias

**Herramientas del agente:**

```python
@tool
def search_documents(query: str) -> str:
    """
    Busca información en los documentos empresariales cargados
    (políticas, reglamentos, manuales). Usar para preguntas sobre
    normativas, procedimientos y reglas de la empresa.
    """

@tool
def get_daily_attendance(date: str) -> str:
    """
    Retorna la asistencia del día indicado.
    Incluye empleados presentes, ausentes y con tardanza.
    Formato de fecha: YYYY-MM-DD.
    """

@tool
def get_employee_attendance(employee_id: int, month: int, year: int) -> str:
    """
    Retorna el resumen de asistencias de un empleado
    en un mes y año específico. Incluye días presentes,
    ausentes, tardanzas y salidas automáticas.
    """

@tool
def get_tardiness_report(month: int, year: int) -> str:
    """
    Retorna lista de empleados con tardanzas en el mes indicado.
    Incluye cantidad de tardanzas por empleado.
    """

@tool
def get_monthly_summary(month: int, year: int) -> str:
    """
    Retorna resumen general de asistencia del mes.
    Incluye porcentaje de asistencia promedio y ausencias.
    """

@tool
def get_employee_info(query: str) -> str:
    """
    Busca información de un empleado por nombre, apellido o legajo.
    Retorna datos básicos del perfil.
    """
```

**Pipeline de ingestión de documentos:**
```
PDF subido por usuario
        ↓
MinIO almacena archivo original
        ↓
FastAPI procesa:
  1. Docling extrae texto
  2. Recursive chunking con overlap
  3. SentenceTransformers genera embeddings
        ↓
pgvector almacena chunks + embeddings + metadatos
```

**Metadatos por chunk:**
```json
{
  "document_id": "uuid",
  "document_name": "Reglamento Interno.pdf",
  "tipo": "documento_empresa",
  "chunk_index": 0
}
```

---

## 6. Modelo de datos

### Tabla: users
```sql
CREATE TABLE users (
  id          SERIAL PRIMARY KEY,
  email       VARCHAR(255) UNIQUE NOT NULL,
  password    VARCHAR(255) NOT NULL,
  role        VARCHAR(50) NOT NULL, -- 'admin' | 'rrhh'
  is_active   BOOLEAN DEFAULT true,
  created_at  TIMESTAMP DEFAULT NOW()
);
```

### Tabla: employees
```sql
CREATE TABLE employees (
  id            SERIAL PRIMARY KEY,
  first_name    VARCHAR(100) NOT NULL,
  last_name     VARCHAR(100) NOT NULL,
  email         VARCHAR(255) UNIQUE,
  legajo        VARCHAR(50) UNIQUE NOT NULL,
  rfid_code     VARCHAR(100) UNIQUE NOT NULL,
  department    VARCHAR(100),
  status        VARCHAR(20) DEFAULT 'ACTIVO', -- 'ACTIVO' | 'INACTIVO'
  created_at    TIMESTAMP DEFAULT NOW(),
  updated_at    TIMESTAMP DEFAULT NOW()
);
```

### Tabla: attendance_records
```sql
CREATE TABLE attendance_records (
  id              SERIAL PRIMARY KEY,
  employee_id     INTEGER REFERENCES employees(id),
  timestamp       TIMESTAMP NOT NULL,
  record_type     VARCHAR(20) NOT NULL, -- 'ENTRADA' | 'SALIDA' | 'INTERMEDIO'
  is_late         BOOLEAN DEFAULT false,
  auto_generated  BOOLEAN DEFAULT false,
  created_at      TIMESTAMP DEFAULT NOW()
);
```

### Tabla: documents
```sql
CREATE TABLE documents (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          VARCHAR(255) NOT NULL,
  minio_path    VARCHAR(500) NOT NULL,
  status        VARCHAR(20) DEFAULT 'PROCESSING', -- 'PROCESSING' | 'READY' | 'ERROR'
  uploaded_by   INTEGER REFERENCES users(id),
  created_at    TIMESTAMP DEFAULT NOW()
);
```

### Tabla: document_chunks (pgvector)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
  id            SERIAL PRIMARY KEY,
  document_id   UUID REFERENCES documents(id) ON DELETE CASCADE,
  content       TEXT NOT NULL,
  embedding     vector(384),
  chunk_index   INTEGER NOT NULL,
  created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON document_chunks
USING ivfflat (embedding vector_cosine_ops);
```

### Tabla: chat_history
```sql
CREATE TABLE chat_history (
  id          SERIAL PRIMARY KEY,
  user_id     INTEGER REFERENCES users(id),
  role        VARCHAR(20) NOT NULL, -- 'user' | 'assistant'
  content     TEXT NOT NULL,
  created_at  TIMESTAMP DEFAULT NOW()
);
```

---

## 7. Flujos de operación críticos

### Flujo 1 — Registro de asistencia IoT
```
Pico 2W lee tarjeta RFID
        ↓
Publica MQTT: { rfid_code: "ABC123" }
        ↓
NestJS recibe evento
        ↓
Busca empleado por rfid_code
        ↓
¿Empleado existe y está ACTIVO?
  NO → descarta evento
  SÍ → continúa
        ↓
¿Cuántos registros tiene hoy?
  0 → tipo: ENTRADA, verifica tardanza
  1 → tipo: SALIDA
  2+ → tipo: INTERMEDIO
        ↓
Persiste en attendance_records
        ↓
Actualiza métricas del dashboard
```

### Flujo 2 — Ingestión de documento
```
Usuario sube PDF desde frontend
        ↓
NestJS recibe archivo
        ↓
Almacena en MinIO
        ↓
Crea registro en tabla documents (status: PROCESSING)
        ↓
Llama a FastAPI /documents/process
        ↓
FastAPI ejecuta pipeline:
  1. Docling extrae texto del PDF
  2. Recursive chunking con overlap 10%
  3. SentenceTransformers genera embeddings (384 dimensiones)
  4. Almacena chunks en document_chunks con embeddings
        ↓
Actualiza status del documento a READY
        ↓
Frontend notifica al usuario
```

### Flujo 3 — Consulta al agente RAG
```
Usuario escribe pregunta en el chat
        ↓
Next.js llama a FastAPI /agent/chat
        ↓
FastAPI pasa pregunta al agente LangChain
        ↓
Agente analiza la pregunta y decide herramienta:
  ├── Sobre políticas/documentos → search_documents
  ├── Sobre asistencia del día → get_daily_attendance
  ├── Sobre asistencia de empleado → get_employee_attendance
  ├── Sobre tardanzas → get_tardiness_report
  ├── Sobre resumen mensual → get_monthly_summary
  └── Sobre datos de empleado → get_employee_info
        ↓
Agente obtiene resultado de la herramienta
        ↓
Groq (Llama 3.1 8B) genera respuesta en lenguaje natural
        ↓
FastAPI persiste pregunta y respuesta en chat_history
        ↓
Retorna respuesta al frontend
```

---

## 8. Dashboard — métricas

El dashboard del responsable de RRHH muestra:

- **Asistencia del día:** porcentaje de empleados presentes vs total activos
- **Promedio mensual:** porcentaje de asistencia del mes en curso
- **Tardanzas del mes:** lista de empleados con tardanzas y cantidad
- **Ausentes hoy:** lista de empleados que no registraron entrada

---

## 9. Autenticación y roles

### Endpoints de auth (NestJS)
- `POST /auth/login` → retorna JWT
- `POST /auth/logout`
- `GET /auth/me` → retorna usuario actual

### Guards
- `JwtAuthGuard` → verifica token en todas las rutas protegidas
- `RolesGuard` → verifica rol requerido por cada endpoint

### Permisos por rol

| Acción | Admin | RRHH |
|---|---|---|
| Crear responsable RRHH | ✅ | ❌ |
| Gestionar empleados | ✅ | ✅ |
| Ver dashboard | ✅ | ✅ |
| Cargar documentos | ✅ | ✅ |
| Consultar agente | ✅ | ✅ |

---

## 10. Variables de entorno (.env.example)

```env
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=kuaai
POSTGRES_USER=kuaai_user
POSTGRES_PASSWORD=kuaai_password

# MinIO
MINIO_ENDPOINT=minio
MINIO_PORT=9000
MINIO_ACCESS_KEY=kuaai_access
MINIO_SECRET_KEY=kuaai_secret
MINIO_BUCKET_DOCUMENTS=documents

# MQTT
MQTT_HOST=mosquitto
MQTT_PORT=1883
MQTT_TOPIC_ATTENDANCE=attendance/checkin

# JWT
JWT_SECRET=your_jwt_secret_here
JWT_EXPIRATION=24h

# Groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

# SentenceTransformers
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
EMBEDDINGS_DIMENSIONS=384

# NestJS
NEST_PORT=3001

# FastAPI
FASTAPI_PORT=8000

# Next.js
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXT_PUBLIC_AI_API_URL=http://localhost:8000
```

---

## 11. Docker Compose — servicios

```yaml
services:
  frontend:
    build: ./apps/frontend
    ports: ["3000:3000"]
    depends_on: [backend-nest]

  backend-nest:
    build: ./apps/backend-nest
    ports: ["3001:3001"]
    depends_on: [postgres, mosquitto, minio]

  backend-fastapi:
    build: ./apps/backend-fastapi
    ports: ["8000:8000"]
    depends_on: [postgres, minio]

  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    volumes: [minio_data:/data]
    command: server /data --console-address ":9001"

  mosquitto:
    image: eclipse-mosquitto
    ports: ["1883:1883"]
    volumes: [./mosquitto.conf:/mosquitto/config/mosquitto.conf]

volumes:
  postgres_data:
  minio_data:
```

---

## 12. Orden de implementación

### Fase 1 — Infraestructura base
- [ ] Estructura del monorepo
- [ ] Docker Compose con todos los servicios
- [ ] Variables de entorno
- [ ] PostgreSQL con pgvector habilitado y tablas creadas
- [ ] MinIO con bucket inicial
- [ ] Mosquitto configurado

### Fase 2 — Backend NestJS
- [ ] Proyecto NestJS inicial
- [ ] Módulo de autenticación (JWT + roles)
- [ ] Módulo de empleados (CRUD)
- [ ] Suscripción MQTT y lógica de asistencia
- [ ] Cron job para salida automática a las 16:00
- [ ] Endpoints de dashboard

### Fase 3 — Backend FastAPI
- [ ] Proyecto FastAPI inicial
- [ ] Endpoint de ingestión de documentos
- [ ] Pipeline: Docling → chunks → SentenceTransformers → pgvector
- [ ] Herramientas del agente LangChain
- [ ] Endpoint de chat con el agente
- [ ] Persistencia de historial de chat

### Fase 4 — Frontend Next.js
- [ ] Proyecto Next.js inicial con Tailwind + shadcn/ui
- [ ] Página de login
- [ ] Dashboard con métricas de asistencia
- [ ] Módulo de gestión de empleados
- [ ] Módulo de carga de documentos
- [ ] Interfaz de chat con el agente

### Fase 5 — IoT Node
- [ ] Firmware MicroPython para Raspberry Pi Pico 2W
- [ ] Lectura de tarjetas RFID RC522
- [ ] Publicación MQTT
- [ ] Manejo de errores y reconexión automática

### Fase 6 — Integración y pruebas
- [ ] Pruebas end-to-end de todos los flujos
- [ ] Optimización de prompts del agente
- [ ] Documentación técnica

---

## 13. Roadmap futuro (fuera del MVP)

- CV de empleados vinculado al perfil con búsqueda semántica
- Migración de Groq a Ollama local para privacidad total
- Sistema de roles granular
- Portal de autogestión para empleados
- Módulo de nómina
- Reportes exportables en PDF
- WebSockets para dashboard en tiempo real
- Industrialización del nodo IoT (PCB + gabinete)
- Deploy en VPS con Ollama local