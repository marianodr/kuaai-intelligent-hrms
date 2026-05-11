# Phase 1 — Infrastructure Base

## Lo que se implementó

Configuración completa del monorepo y todos los servicios de infraestructura que soportan el sistema Kuaai. Esta fase no contiene lógica de negocio: establece la base sobre la que se construyen las fases 2, 3 y 4.

- Estructura de monorepo con 4 aplicaciones bajo `apps/`
- Docker Compose con 6 servicios orquestados y healthchecks
- PostgreSQL 16 con extensión `pgvector` y las 6 tablas del modelo de datos
- MinIO con bucket `documents` creado automáticamente al iniciar
- Mosquitto MQTT broker configurado en puerto 1883
- Variables de entorno centralizadas en `.env.example`
- `.gitignore` para Node, Python, Docker y secretos

---

## Estructura de archivos creados

```
kuaai-intelligent-hrms/
├── apps/
│   ├── frontend/           # (vacío) Next.js 14 — Fase 4
│   ├── backend-nest/       # (vacío) NestJS — Fase 2
│   ├── backend-fastapi/    # (vacío) FastAPI — Fase 3
│   └── iot-node/           # MicroPython (código previo migrado)
├── infra/
│   ├── postgres/
│   │   └── init.sql        # CREATE EXTENSION vector + 6 tablas + índices + trigger
│   ├── minio/
│   │   └── init-minio.sh   # Script que crea el bucket 'documents' via mc
│   └── mosquitto/
│       └── mosquitto.conf  # Listener 1883, persistencia, logs stdout
├── docker-compose.yml      # Producción: healthchecks, depends_on, restart
├── docker-compose.dev.yml  # Desarrollo: volumes con hot-reload
├── .env.example            # Plantilla de todas las variables de entorno
└── .gitignore              # Node, Python, .env, Docker volumes
```

---

## Servicios Docker Compose

| Servicio | Imagen | Puerto(s) | Descripción |
|----------|--------|-----------|-------------|
| `postgres` | `pgvector/pgvector:pg16` | `5432` | PostgreSQL con extensión vector. Init automático via `init.sql` |
| `minio` | `minio/minio:latest` | `9000` (API), `9001` (Console) | Object storage para PDFs |
| `minio-init` | `minio/mc:latest` | — | Job de init: crea bucket `documents` y termina |
| `mosquitto` | `eclipse-mosquitto:2` | `1883` | MQTT broker para eventos del nodo IoT |
| `backend-nest` | Build local | `3001` | NestJS (vacío en Fase 1) |
| `backend-fastapi` | Build local | `8000` | FastAPI (vacío en Fase 1) |
| `frontend` | Build local | `3000` | Next.js (vacío en Fase 1) |

**Healthchecks configurados:**
- `postgres`: `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` (interval: 10s, retries: 5)
- `minio`: `mc ready local` (interval: 10s, retries: 5)
- `backend-nest` y `backend-fastapi` dependen de `postgres` con `condition: service_healthy`

---

## Variables de entorno configuradas

Todas las variables están en `.env.example`. Para desarrollo, copiar como `.env`:

```bash
cp .env.example .env
# Completar GROQ_API_KEY y JWT_SECRET con valores reales
```

| Variable | Valor por defecto | Obligatoria |
|----------|-------------------|:-----------:|
| `POSTGRES_HOST` | `postgres` | — |
| `POSTGRES_PORT` | `5432` | — |
| `POSTGRES_DB` | `kuaai` | — |
| `POSTGRES_USER` | `kuaai_user` | — |
| `POSTGRES_PASSWORD` | `kuaai_password` | — |
| `MINIO_ENDPOINT` | `minio` | — |
| `MINIO_PORT` | `9000` | — |
| `MINIO_ACCESS_KEY` | `kuaai_access` | — |
| `MINIO_SECRET_KEY` | `kuaai_secret` | — |
| `MINIO_BUCKET_DOCUMENTS` | `documents` | — |
| `MQTT_HOST` | `mosquitto` | — |
| `MQTT_PORT` | `1883` | — |
| `MQTT_TOPIC_ATTENDANCE` | `attendance/checkin` | — |
| `JWT_SECRET` | — | ✅ |
| `JWT_EXPIRATION` | `24h` | — |
| `GROQ_API_KEY` | — | ✅ |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | — |
| `EMBEDDINGS_MODEL` | `all-MiniLM-L6-v2` | — |
| `EMBEDDINGS_DIMENSIONS` | `384` | — |
| `NEST_PORT` | `3001` | — |
| `FASTAPI_PORT` | `8000` | — |
| `NEXT_PUBLIC_API_URL` | `http://localhost:3001` | — |
| `NEXT_PUBLIC_AI_API_URL` | `http://localhost:8000` | — |

---

## Cómo probarlo

### Levantar todos los servicios de infraestructura

```bash
# Copiar y configurar variables
cp .env.example .env

# Levantar solo infraestructura (sin apps)
docker compose up postgres minio mosquitto -d

# Verificar que postgres levantó con pgvector y las tablas
docker compose exec postgres psql -U kuaai_user -d kuaai -c "\dt"

# Verificar que pgvector está habilitado
docker compose exec postgres psql -U kuaai_user -d kuaai -c "SELECT extname FROM pg_extension;"

# Verificar que el bucket de MinIO fue creado
docker compose run --rm minio-init

# Probar MQTT publicando un mensaje de prueba
docker compose exec mosquitto mosquitto_pub \
  -h localhost -p 1883 \
  -t attendance/checkin \
  -m '{"rfid_code":"TEST001"}'
```

### Acceso a la consola de MinIO

Abrir `http://localhost:9001` en el navegador.
- Usuario: `kuaai_access`
- Contraseña: `kuaai_secret`

### Levantar stack completo (modo desarrollo)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Decisiones técnicas tomadas

### pgvector sobre PostgreSQL 16
Se eligió `pgvector/pgvector:pg16` como imagen base para unificar datos relacionales y vectores en un solo motor. Evita mantener un segundo servicio de vector store (Qdrant, Weaviate) y simplifica el deployment para un MVP académico. Ver [ADR-001](../decisions/ADR-001-pgvector-vs-qdrant.md).

### `synchronize: false` en TypeORM
Las tablas se crean exclusivamente vía `infra/postgres/init.sql`. Esto garantiza control total sobre los índices (especialmente `ivfflat` de pgvector) y constraints, que TypeORM no genera correctamente para tipos custom como `vector`.

### MinIO sobre S3/Storage externo
MinIO es un object storage compatible con S3 que corre como contenedor Docker. Para el MVP evita dependencia de servicios cloud externos y permite operar offline (relevante para PyMEs de Misiones con conectividad variable).

### `minio-init` como job separado
El bucket se crea en un contenedor `minio/mc` que ejecuta el script y termina (`exit 0`). Docker Compose lo trata como un job de inicialización gracias a que no tiene `restart: unless-stopped`.

### Mosquitto con `allow_anonymous: true`
Configuración apropiada para desarrollo y MVP. En producción debería configurarse autenticación por contraseña o certificados TLS. La red Docker interna ya limita el acceso externo.

---

## Pendientes para fases siguientes

- [ ] **Fase 2:** Implementar `apps/backend-nest/` con Dockerfile funcional
- [ ] **Fase 3:** Implementar `apps/backend-fastapi/` con Dockerfile funcional
- [ ] **Fase 4:** Implementar `apps/frontend/` con Dockerfile funcional
- [ ] **Producción:** Configurar autenticación MQTT (usuario/contraseña o TLS)
- [ ] **Producción:** Cambiar `allow_anonymous false` en `mosquitto.conf`
- [ ] **Producción:** Rotar credenciales por defecto de MinIO y PostgreSQL
- [ ] Eliminar directorio `iot-node/` de la raíz (ya migrado a `apps/iot-node/`)
