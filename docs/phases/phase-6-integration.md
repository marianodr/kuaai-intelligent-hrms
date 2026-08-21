# Fase 6 — Integración y pruebas

## Entregables

| Artefacto | Descripción |
|---|---|
| `infra/postgres/seed.sql` | 2 usuarios + 8 empleados + registros de asistencia de mayo 2026 |
| `scripts/seed-db.sh` | Carga seed.sql en el contenedor postgres vía docker exec |
| `scripts/test-e2e.sh` | Script E2E con 19 checks sobre los 6 flujos del sistema |
| `scripts/test-agent-tools.py` | Verificación tool-por-tool del agente RAG (6 herramientas): invocación correcta, argumentos y aplicación del resultado en la respuesta final |
| `apps/backend-fastapi/app/services/agent_service.py` | Prompt del agente optimizado con fecha dinámica |
| `README.md` | Documentación principal del monorepo |

---

## Seed de datos de prueba

### Usuarios

| Email | Contraseña | Rol |
|---|---|---|
| admin@kuaai.com | admin123 | admin |
| rrhh@kuaai.com | rrhh123 | rrhh |

### Empleados

| Legajo | Nombre | Departamento | rfid_code |
|---|---|---|---|
| EMP-001 | Juan García | Administración | 37194205 |
| EMP-002 | María López | Administración | 346298099 |
| EMP-003 | Pedro Ramírez | Operaciones | 112233445 |
| EMP-004 | Ana Fernández | Operaciones | 556677889 |
| EMP-005 | Carlos Martínez | Operaciones | 998877665 |
| EMP-006 | Laura Giménez | Ventas | 443322110 |
| EMP-007 | Roberto Torres | Ventas | 667788990 |
| EMP-008 | Sofía Benítez | Ventas | 221100334 |

### Asistencias cargadas (mayo 2026)

| Día | Presentes | Ausentes | Tardanzas |
|---|---|---|---|
| Lunes 04/05 | 8/8 | — | EMP-003, EMP-007 |
| Martes 06/05 | 7/8 | EMP-005 | EMP-002, EMP-007 |
| Miércoles 07/05 | 8/8 | — | EMP-007 |
| Jueves 08/05 | 6/8 | EMP-003, EMP-007 | EMP-005 |
| Viernes 09/05 | 8/8 | — | EMP-005 |
| Lunes 12/05 | 6/8 | EMP-004, EMP-006 | EMP-003 |

---

## Optimización del agente RAG

### Cambios al `SYSTEM_PROMPT`

**Antes:** prompt estático sin contexto de fecha, reglas genéricas.

**Después:**
- Fecha del día inyectada dinámicamente (`{today}`, `{year}`) en cada invocación via `date.today()`
- Guía explícita de cuándo usar cada herramienta con sus parámetros requeridos
- Indicación de usar `get_employee_info` primero para obtener el ID antes de `get_employee_attendance`
- Instrucción de no inventar datos

### Por qué inyección dinámica y no en `init_agent`

El agente se inicializa una sola vez al arrancar FastAPI. Si el prompt se inyecta ahí, el agente tendría la fecha de inicio del servidor toda su vida. La inyección por invocación en `chat()` garantiza que el agente siempre tenga la fecha correcta.

---

## Script de prueba E2E

`scripts/test-e2e.sh` cubre 19 checks distribuidos en 6 secciones:

| Sección | Checks |
|---|---|
| 0. Health | NestJS responde, FastAPI /health = 200 |
| 1. Auth | Login → token, user.id, role=admin |
| 2. Empleados | List, create, update, deactivate |
| 3. Dashboard | today, monthly-average, tardiness |
| 4. MQTT | Publicación de fichaje RFID simulado |
| 5. Documentos | GET /documents/ retorna array |
| 6. Agente RAG | Crea hilo real (`POST /threads`), chat responde 2xx (no error HTTP), answer no vacío, history retorna array |

**Uso:**
```bash
# Con stack corriendo y seed cargado:
./scripts/test-e2e.sh
```

> `thread_id` en `POST /agent/chat` debe ser un UUID con fila real en `conversation_threads`
> (FK agregada en `002_conversation_threads.sql`) — por eso el script crea un hilo antes de
> llamar al agente, en vez de pasar un string arbitrario.

### Verificación tool-por-tool del agente

`test-e2e.sh` solo confirma que `/agent/chat` responde con un `answer` no vacío — no valida
qué herramienta usó el agente ni si el resultado de esa herramienta se refleja en la respuesta.
Para eso está `scripts/test-agent-tools.py`, que envía una pregunta representativa por cada una
de las 6 herramientas (`search_documents`, `get_daily_attendance`, `get_employee_attendance`,
`get_tardiness_report`, `get_monthly_summary`, `get_employee_info`) y verifica, por herramienta:

1. se invocó la herramienta esperada (y ninguna otra fuera de las permitidas como prerequisito)
2. los argumentos generados son razonables para la pregunta
3. la respuesta final del agente refleja el resultado real de la herramienta, no una respuesta genérica

Esto requiere que `POST /agent/chat` exponga qué herramientas invocó en el campo `tool_calls`
de la respuesta (`apps/backend-fastapi/app/routers/agent.py` +
`app/services/agent_service.py`), reconstruido a partir de los mensajes intermedios que
`create_react_agent` ya arma internamente (`AIMessage.tool_calls` + `ToolMessage`), sin cambiar
la lógica del agente.

**Uso:**
```bash
# Con stack corriendo y seed cargado:
python3 scripts/test-agent-tools.py
```

---

## Checklist de integración manual

### Flujo 1 — IoT → Asistencia

- [ ] Conectar Pico 2W con `secrets.py` configurado con IP del host
- [ ] Acercar tarjeta → LED amarillo + buzzer = evento publicado
- [ ] Verificar en `GET /dashboard/today` que el empleado aparece como presente
- [ ] Acercar de nuevo la misma tarjeta → aparece como SALIDA

### Flujo 2 — Ingestión de documentos

- [ ] Login en frontend → ir a Documentos
- [ ] Subir un PDF (ej: reglamento interno)
- [ ] Estado cambia de PROCESSING → READY en ~30 segundos
- [ ] Ir al chat y preguntar algo relacionado con el contenido del PDF

### Flujo 3 — Agente RAG

Consultas de prueba con los datos de seed:

```
¿Cuántos empleados vinieron hoy?
¿Quiénes llegaron tarde en mayo de 2026?
Dame el resumen de asistencia de mayo
¿En qué departamento trabaja Pedro Ramírez?
¿Cuál fue el porcentaje de asistencia del lunes 4 de mayo?
```

---

## Pendientes post-MVP

Ítems identificados durante la integración que quedan fuera del alcance del PFG:

- WebSockets para actualización del dashboard en tiempo real (actualmente requiere refresh manual)
- Exportación de reportes a PDF
- Notificaciones cuando un empleado no registra salida
- Test de carga del agente con múltiples usuarios concurrentes
- Hardening de seguridad: rate limiting en endpoints de auth, headers CORS más restrictivos en producción
