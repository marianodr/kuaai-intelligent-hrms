# Architecture Overview

## Descripción del sistema

**Kuaai** (del guaraní *kuaa*: saber, conocimiento) es un MVP de Sistema de Gestión de Recursos Humanos (HRMS) inteligente orientado a PyMEs de la región de Misiones, Argentina.

Combina tres capacidades principales:
1. **Control de asistencias IoT:** un nodo Raspberry Pi Pico 2W con lector RFID registra entradas y salidas de empleados en tiempo real mediante MQTT.
2. **Gestión de RRHH:** CRUD de empleados, métricas del dashboard y autenticación con roles (Admin / Responsable de RRHH).
3. **Agente RAG inteligente:** permite realizar consultas en lenguaje natural sobre documentos empresariales (reglamentos, políticas, manuales) y datos estructurados de asistencia.

---

## Patrones arquitectónicos

El sistema combina tres patrones arquitectónicos complementarios:

### 1. Orientada a eventos (Event-Driven)
El nodo IoT publica eventos MQTT al broker Mosquitto cada vez que un empleado acerca su tarjeta RFID. NestJS consume estos eventos de forma asincrónica y persiste los registros en PostgreSQL sin bloquear el hardware.

```
[Pico 2W + RFID] --MQTT--> [Mosquitto] --subscribe--> [NestJS AttendanceService]
```

### 2. Cliente-Servidor en tres capas con proxy
El frontend Next.js habla **únicamente** con NestJS. NestJS actúa como API gateway: maneja auth, empleados y dashboard directamente, y hace de proxy hacia FastAPI para documentos y chat.

```
[Next.js] --REST--> [NestJS]              (auth, CRUD, dashboard)
                       └── proxy -->  [FastAPI]   (RAG, chat, documentos)
```

Este patrón tiene dos beneficios: el frontend no necesita conocer la URL interna de FastAPI, y NestJS puede aplicar el guard JWT antes de dejar pasar la solicitud al servicio de IA.

### 3. Agéntico (Agentic RAG)
El agente LangChain orquesta dinámicamente múltiples herramientas para responder consultas en lenguaje natural. Decide en tiempo de ejecución qué herramienta usar (búsqueda semántica en pgvector, consultas SQL estructuradas, o ambas) según la intención del usuario.

```
[Pregunta usuario] --> [Agente ReAct] --> [Tool: search_documents / get_attendance / ...]
                                                    |
                                          [pgvector / PostgreSQL]
                                                    |
                                       [Groq LLM genera respuesta]
```

---

## Diagrama de contenedores (Nivel 2)

```mermaid
graph TB
    USER["👤 Usuario\n(Admin / RRHH)"]
    IOT["📟 Nodo IoT\n(Pico 2W + RC522)"]
    GROQ["☁️ Groq API\n(Llama 3.1 8B)"]

    subgraph PRES ["Presentación"]
        FE["🌐 Frontend\nNext.js + Tailwind + shadcn/ui\n:3000"]
    end

    subgraph APP ["Aplicación"]
        NEST["⚙️ Backend NestJS\nAuth · CRUD · MQTT · Dashboard\n:3001"]
        FAPI["🤖 Backend FastAPI\nRAG · Agente · Embeddings\n:8000"]
    end

    subgraph MSG ["Mensajería"]
        MQTT["📡 Mosquitto\nMQTT Broker\n:1883"]
    end

    subgraph DATA ["Datos"]
        PG[("🐘 PostgreSQL + pgvector\n:5432")]
        MINIO["🪣 MinIO\nObject Storage\n:9000"]
    end

    USER  -->|"HTTPS :3000"| FE
    FE    -->|"REST — todas las rutas"| NEST
    NEST  -->|"proxy docs + agente"| FAPI
    NEST  -->|"Leer/Escribir"| PG
    NEST  -->|"Subir PDFs"| MINIO
    NEST  -->|"subscribe"| MQTT
    FAPI  -->|"vectores"| PG
    FAPI  -->|"descargar PDFs"| MINIO
    FAPI  -->|"inferencia LLM"| GROQ
    IOT   -->|"publish RFID"| MQTT

    style FE   fill:#3b82f6,color:#fff
    style NEST fill:#16a34a,color:#fff
    style FAPI fill:#dc2626,color:#fff
    style PG   fill:#6366f1,color:#fff
    style MINIO fill:#f59e0b,color:#fff
    style MQTT fill:#8b5cf6,color:#fff
    style USER fill:#0f172a,color:#fff
    style IOT  fill:#0f172a,color:#fff
    style GROQ fill:#374151,color:#fff
```

---

## Responsabilidades por servicio

| Servicio | Tecnología | Responsabilidades |
|----------|-----------|-------------------|
| **Frontend** | Next.js 14 + Tailwind + shadcn/ui | Login, dashboard de asistencias, gestión de empleados, carga de documentos, chat con el agente |
| **Backend NestJS** | NestJS + TypeORM + Passport | Auth JWT con roles, CRUD empleados, suscripción MQTT, lógica de asistencia, cron 16:00, métricas dashboard. Actúa como **API gateway/proxy** hacia FastAPI para las rutas de documentos y agente |
| **Backend FastAPI** | FastAPI + LangChain + Groq | Ingestión de PDFs, pipeline de embeddings, agente RAG, endpoints de chat, historial de conversación. Solo accesible desde NestJS en producción |
| **PostgreSQL + pgvector** | PostgreSQL 16 | Datos relacionales (empleados, asistencias, usuarios, documentos) + vectores de embeddings (384 dims) |
| **MinIO** | MinIO (S3-compatible) | Almacenamiento de archivos PDF originales subidos por usuarios |
| **Mosquitto** | Eclipse Mosquitto 2 | Broker MQTT que recibe eventos del nodo IoT y los distribuye a los suscriptores |
| **Nodo IoT** | Raspberry Pi Pico 2W + MicroPython | Lee UIDs de tarjetas RFID RC522 y publica en topic `attendance/checkin` |

---

## Stack tecnológico completo

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Frontend | Next.js + TypeScript + Tailwind CSS + shadcn/ui | 14+ |
| Backend principal | NestJS + TypeScript | 10+ |
| Backend IA | FastAPI + Python | 0.115+ |
| Base de datos | PostgreSQL + pgvector | 16 |
| Object storage | MinIO | Latest |
| Mensajería IoT | MQTT + Eclipse Mosquitto | 2 |
| LLM | Groq API — Llama 3.1 8B Instant | — |
| Embeddings | SentenceTransformers — all-MiniLM-L6-v2 | 384 dims |
| Extracción PDF | Docling | 2+ |
| Framework agente | LangChain + LangGraph | 0.3+ / 1.2+ |
| ORM | TypeORM | 0.3+ |
| Autenticación | JWT + Passport.js | — |
| Contenedorización | Docker + Docker Compose | — |
| IoT Firmware | MicroPython | — |
| Hardware IoT | Raspberry Pi Pico 2W + RFID RC522 | — |
