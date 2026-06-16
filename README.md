<p align="center">
  <img src="apps/frontend/public/logo-login.png" alt="Kuaai HRMS" width="200"/>
</p>

# Kuaai HRMS

Sistema de Gestión de Recursos Humanos inteligente para PyMEs de Misiones, Argentina.
Combina control de asistencia por RFID/IoT, gestión de empleados y un agente RAG para consultas en lenguaje natural.

**Proyecto Final de Grado — Universidad Nacional de Misiones (UNaM)**
**Autor:** Mariano David Rodriguez

---

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | Next.js 16 + Tailwind CSS + shadcn/ui |
| Backend principal | NestJS + TypeORM + JWT |
| Backend IA | FastAPI + LangChain + Groq (Llama 3.1 8B) |
| Base de datos | PostgreSQL 16 + pgvector |
| Object storage | MinIO |
| Broker IoT | Mosquitto MQTT |
| IoT node | Raspberry Pi Pico 2W + RC522 + MicroPython |
| Contenedorización | Docker + Docker Compose |

---

## Requisitos

- Docker 24+ y Docker Compose v2
- Una API key de [Groq](https://console.groq.com) (gratuita)
- (Para el nodo IoT) Raspberry Pi Pico 2W + lector RC522

---

## Arranque rápido

### 1. Clonar y configurar variables de entorno

```bash
git clone <repo-url> kuaai-intelligent-hrms
cd kuaai-intelligent-hrms

cp .env.example .env
```

Editar `.env` y completar obligatoriamente:

```env
JWT_SECRET=cambiar_por_secreto_seguro_de_32_chars
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

### 2. Levantar el stack

```bash
docker compose up --build -d
```

Servicios y puertos:

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| NestJS API | http://localhost:3001 |
| FastAPI + Swagger | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| PostgreSQL | localhost:5432 |
| MQTT | localhost:1883 |

### 3. Cargar datos de prueba

```bash
./scripts/seed-db.sh
```

Esto crea:
- 8 empleados con asistencias de mayo 2026

### 4. Acceder al sistema

Abrir http://localhost:3000 e iniciar sesión con las credenciales de arriba.

---

## Pruebas E2E

Con el stack corriendo y los datos de seed cargados:

```bash
./scripts/test-e2e.sh
```

El script prueba los 6 flujos principales: health, auth, empleados, dashboard, MQTT y agente RAG.

---

## Estructura del monorepo

```
kuaai-intelligent-hrms/
├── apps/
│   ├── frontend/           # Next.js 16 — UI
│   ├── backend-nest/       # NestJS — CRUD, MQTT, auth, dashboard
│   ├── backend-fastapi/    # FastAPI — RAG, agente, ingestión PDF
│   └── iot-node/           # MicroPython — Raspberry Pi Pico 2W
├── infra/
│   ├── postgres/
│   │   ├── init.sql        # Esquema de tablas
│   │   ├── seed.sql        # Datos de prueba
│   │   └── migrations/     # Migraciones incrementales
│   ├── minio/
│   │   └── init-minio.sh   # Crea bucket inicial
│   └── mosquitto/
│       └── mosquitto.conf
├── docs/
│   ├── phases/             # Documentación por fase
│   ├── architecture/       # Diagramas y decisiones de diseño
│   ├── decisions/          # ADRs
│   └── api/                # Referencia de endpoints
├── scripts/
│   ├── test-e2e.sh         # Pruebas de integración
│   └── seed-db.sh          # Carga datos de prueba
├── docker-compose.yml
├── docker-compose.dev.yml  # Overrides para desarrollo con volúmenes
├── .env.example
└── ARCHITECTURE.md         # Diagramas de arquitectura (Mermaid)
```

---

## Flujos principales

### 1. Registro de asistencia IoT

```
Empleado → tarjeta RFID → Pico 2W → MQTT → NestJS → PostgreSQL
```

El Pico 2W lee el UID de la tarjeta y publica en `attendance/checkin`:
```json
{ "rfid_code": "37194205" }
```
NestJS determina si es ENTRADA, SALIDA o INTERMEDIO y registra la asistencia.

**Simulación manual:**
```bash
mosquitto_pub -h localhost -t "attendance/checkin" -m '{"rfid_code":"37194205"}'
```

### 2. Ingestión de documentos

```
PDF → FastAPI → MinIO → Docling → chunks → SentenceTransformers → pgvector
```

Desde el frontend (`/documents`): subir un PDF → el pipeline lo procesa en background y lo deja disponible para el agente.

### 3. Consulta al agente RAG

```
Pregunta → NestJS (proxy) → FastAPI → LangChain ReAct → herramientas SQL/pgvector → Groq → respuesta
```

El agente tiene 6 herramientas:
- `search_documents` — busca en documentos empresariales (pgvector)
- `get_daily_attendance` — asistencia de un día
- `get_employee_attendance` — historial de un empleado
- `get_tardiness_report` — reporte de tardanzas del mes
- `get_monthly_summary` — promedio de asistencia mensual
- `get_employee_info` — busca empleado por nombre o legajo

---

## Desarrollo local (sin Docker)

### NestJS

```bash
cd apps/backend-nest
npm install
cp ../../.env .env     # ajustar POSTGRES_HOST=localhost, etc.
npm run start:dev
```

### FastAPI

```bash
cd apps/backend-fastapi
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../../.env .env
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd apps/frontend
npm install
cp ../../.env .env.local   # ajustar NEXT_PUBLIC_API_URL=http://localhost:3001
npm run dev
```

---

## Nodo IoT

Ver [`apps/iot-node/README.md`](apps/iot-node/README.md) para instrucciones de hardware, pinout y despliegue en la Raspberry Pi Pico 2W.

---

## Documentación

| Recurso | Ubicación |
|---|---|
| Arquitectura completa (diagramas Mermaid) | `ARCHITECTURE.md` |
| Plan de desarrollo original (archivado) | `docs/plan-original.md` |
| Endpoints NestJS | `docs/api/nest-endpoints.md` |
| Endpoints FastAPI | `docs/api/fastapi-endpoints.md` |
| Decisiones de arquitectura (ADR) | `docs/decisions/` |
| Diagramas de base de datos | `docs/architecture/database-schema.md` |
| Herramientas del agente | `docs/architecture/agent-tools.md` |
