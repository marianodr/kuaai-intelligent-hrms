# Phase 2 — Backend NestJS

## Lo que se implementó

Backend principal del sistema en NestJS (TypeScript). Cubre autenticación JWT con roles, CRUD de empleados, procesamiento de eventos IoT via MQTT y endpoints de métricas para el dashboard.

- **AuthModule:** login, JWT strategy, guards `JwtAuthGuard` y `RolesGuard`, decorador `@Roles`
- **UsersModule:** gestión interna de usuarios con hash bcrypt (no expuesto directamente)
- **EmployeesModule:** CRUD completo con paginación y filtros por nombre y departamento
- **AttendanceModule:** lógica de negocio ENTRADA/SALIDA/INTERMEDIO, detección de tardanza
- **MqttModule:** suscripción al topic `attendance/checkin`, reconexión automática
- **DashboardModule:** métricas de asistencia del día, promedio mensual y reporte de tardanzas
- **Cron job:** generación automática de salida a las 16:00 (lunes a viernes)
- **Dockerfile** multi-stage con targets `development` y `production`

---

## Estructura de módulos

```
apps/backend-nest/src/
├── main.ts                          # Bootstrap: ValidationPipe, CORS, puerto 3001
├── app.module.ts                    # Raíz: ConfigModule, TypeOrmModule, ScheduleModule
│
├── auth/
│   ├── auth.module.ts               # JwtModule, PassportModule
│   ├── auth.service.ts              # login(): valida credenciales, firma JWT
│   ├── auth.controller.ts           # POST /auth/login, GET /auth/me, POST /auth/logout
│   ├── strategies/
│   │   └── jwt.strategy.ts          # Valida Bearer token, inyecta user en request
│   ├── guards/
│   │   ├── jwt-auth.guard.ts        # Protege rutas: verifica JWT
│   │   └── roles.guard.ts           # Verifica rol requerido via metadata
│   ├── decorators/
│   │   └── roles.decorator.ts       # @Roles('admin', 'rrhh')
│   └── dto/
│       └── login.dto.ts             # { email, password } con class-validator
│
├── users/
│   ├── users.module.ts
│   ├── users.service.ts             # findByEmail(), createUser() con bcrypt hash
│   └── entities/
│       └── user.entity.ts           # Tabla users: id, email, password, role, is_active
│
├── employees/
│   ├── employees.module.ts
│   ├── employees.service.ts         # findAll (paginado+filtros), findOne, create, update, deactivate
│   ├── employees.controller.ts      # GET/POST/PUT/DELETE /employees
│   ├── entities/
│   │   └── employee.entity.ts       # Tabla employees: id, first_name, legajo, rfid_code, status
│   └── dto/
│       ├── create-employee.dto.ts
│       └── update-employee.dto.ts   # PartialType(Create) + status opcional
│
├── attendance/
│   ├── attendance.module.ts
│   ├── attendance.service.ts        # processRfidEvent(), generateAutoExits() @Cron, getTodayRecords()
│   └── entities/
│       └── attendance-record.entity.ts  # Tabla attendance_records
│
├── dashboard/
│   ├── dashboard.module.ts
│   ├── dashboard.service.ts         # getTodayAttendance(), getMonthlyAverage(), getTardinessReport()
│   └── dashboard.controller.ts      # GET /dashboard/today, /monthly-average, /tardiness
│
└── mqtt/
    ├── mqtt.module.ts
    └── mqtt.service.ts              # OnModuleInit: conecta, suscribe, maneja mensajes y errores
```

---

## Endpoints expuestos

### Auth

| Método | Ruta | Guard | Body | Respuesta |
|--------|------|-------|------|-----------|
| `POST` | `/auth/login` | Público | `{ email, password }` | `{ access_token, user }` |
| `GET` | `/auth/me` | JWT | — | `{ id, email, role }` |
| `POST` | `/auth/logout` | JWT | — | `{ message }` |

### Employees

| Método | Ruta | Guard | Descripción |
|--------|------|-------|-------------|
| `GET` | `/employees` | JWT | Lista paginada. Query: `?page=1&limit=10&name=&department=` |
| `GET` | `/employees/:id` | JWT | Detalle de empleado por ID |
| `POST` | `/employees` | JWT | Crear nuevo empleado |
| `PUT` | `/employees/:id` | JWT | Editar datos del empleado |
| `DELETE` | `/employees/:id` | JWT | Dar de baja (cambia status a `INACTIVO`) |

### Dashboard

| Método | Ruta | Guard | Query params | Descripción |
|--------|------|-------|-------------|-------------|
| `GET` | `/dashboard/today` | JWT | — | Asistencia del día actual |
| `GET` | `/dashboard/monthly-average` | JWT | `?month=5&year=2026` | Promedio de asistencia del mes |
| `GET` | `/dashboard/tardiness` | JWT | `?month=5&year=2026` | Empleados con tardanzas |

---

## Lógica de asistencia (AttendanceService)

El método `processRfidEvent(rfidCode)` es invocado por el `MqttService` cada vez que llega un mensaje al topic `attendance/checkin`.

```
Evento MQTT { rfid_code: "ABC123" }
        │
        ▼
¿Empleado existe y status = 'ACTIVO'?
  NO → log WARN, descarta evento
  SÍ → continúa
        │
        ▼
Cuenta registros con record_type = 'ENTRADA' del día actual
        │
        ├── 0 registros → record_type = 'ENTRADA'
        │                  ¿timestamp.hour > 08:15? → is_late = true
        │
        ├── 1 registro  → record_type = 'SALIDA'
        │
        └── 2+ registros → record_type = 'INTERMEDIO'
        │
        ▼
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late, auto_generated=false)
```

**Horario laboral:**
- Entrada esperada: `08:00`
- Tolerancia para tardanza: 15 minutos → tardanza si llega después de las `08:15`
- Salida esperada: `16:00`

---

## Cron job — Salida automática

```typescript
@Cron('0 16 * * 1-5')   // 16:00hs, lunes a viernes
async generateAutoExits(): Promise<void>
```

Lógica ejecutada a las 16:00 de cada día hábil:

1. Obtiene lista de todos los empleados con `status = 'ACTIVO'`
2. Para cada empleado, verifica si tiene registro de `ENTRADA` en el día
3. Si tiene `ENTRADA` pero no tiene `SALIDA` → genera registro con:
   - `record_type = 'SALIDA'`
   - `auto_generated = true`
   - `timestamp = now()` (16:00)
4. Si no tiene `ENTRADA`, lo omite (ausente del día)

---

## Cómo probarlo

### Iniciar el servicio en desarrollo

```bash
cd apps/backend-nest
npm install
cp ../../.env.example ../../.env   # configurar variables primero
npm run start:dev
```

### Login y obtención de token

```bash
# Login (devuelve access_token)
curl -X POST http://localhost:3001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@kuaai.com","password":"admin123"}'

# Guardar token para los siguientes requests
TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

### Empleados

```bash
# Listar empleados (paginado)
curl http://localhost:3001/employees?page=1&limit=10 \
  -H "Authorization: Bearer $TOKEN"

# Filtrar por nombre
curl "http://localhost:3001/employees?name=garcia" \
  -H "Authorization: Bearer $TOKEN"

# Crear empleado
curl -X POST http://localhost:3001/employees \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Juan",
    "last_name": "García",
    "email": "juan.garcia@empresa.com",
    "legajo": "EMP-001",
    "rfid_code": "A1B2C3D4",
    "department": "Administración"
  }'

# Dar de baja
curl -X DELETE http://localhost:3001/employees/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Dashboard

```bash
# Asistencia del día
curl http://localhost:3001/dashboard/today \
  -H "Authorization: Bearer $TOKEN"

# Promedio mensual (mayo 2026)
curl "http://localhost:3001/dashboard/monthly-average?month=5&year=2026" \
  -H "Authorization: Bearer $TOKEN"

# Reporte de tardanzas
curl "http://localhost:3001/dashboard/tardiness?month=5&year=2026" \
  -H "Authorization: Bearer $TOKEN"
```

### Simular evento MQTT del nodo IoT

```bash
# Con mosquitto_pub instalado localmente
mosquitto_pub -h localhost -p 1883 \
  -t attendance/checkin \
  -m '{"rfid_code":"A1B2C3D4"}'

# Alternativa: desde el contenedor de Mosquitto
docker compose exec mosquitto mosquitto_pub \
  -h localhost -p 1883 \
  -t attendance/checkin \
  -m '{"rfid_code":"A1B2C3D4"}'
```

---

## Decisiones técnicas tomadas

### Separación NestJS / FastAPI
NestJS maneja todo lo relacionado con el dominio HRMS (empleados, asistencias, auth) porque TypeScript y el ecosistema NestJS son ideales para APIs REST tipadas con guards, pipes y módulos. FastAPI se reserva para el dominio IA (RAG, embeddings, LangChain), donde Python tiene ventaja absoluta en librerías. Ver [ADR-002](../decisions/ADR-002-nestjs-fastapi-split.md).

### `synchronize: false` en TypeORM
Las entidades TypeORM mapean las tablas existentes creadas por `init.sql` pero no las modifican. Esto evita que TypeORM rompa los índices `ivfflat` de pgvector o los constraints personalizados al reiniciar.

### Lógica ENTRADA/SALIDA/INTERMEDIO por conteo
En vez de rastrear estado explícito por empleado, se cuenta el número de registros de ese día. Es simple, robusto ante reinicios y fácil de auditar en la base de datos. El caso borde de "más de 2 registros" se trata como INTERMEDIO para no bloquear a empleados que salen y vuelven.

### Reconexión automática MQTT
`MqttService` usa `reconnectPeriod: 5000` del cliente MQTT para reconectarse automáticamente si el broker reinicia. Esto es crítico para el IoT: el nodo Pico 2W puede seguir publicando aunque el backend se haya reiniciado brevemente.

### bcrypt con saltRounds = 10
Balance razonable entre seguridad y performance para un MVP. En producción con carga alta se podría reducir a 8 o migrar a argon2.

---

## Pendientes para fases siguientes

- [ ] **Fase 4:** Endpoint `POST /documents/upload` en NestJS que recibe el PDF, lo sube a MinIO y llama a FastAPI `/documents/process`
- [ ] **Fase 4:** Integración con el frontend Next.js
- [ ] Seed inicial de datos: crear usuario `admin` por defecto al primer arranque
- [ ] Endpoint `POST /users` (solo admin) para crear responsables de RRHH
- [ ] Tests unitarios para `AttendanceService.processRfidEvent()`
- [ ] Manejo de zona horaria: actualmente usa `new Date()` del servidor; definir TZ explícita para Argentina (UTC-3)
- [ ] Rate limiting en `/auth/login` para prevenir fuerza bruta
