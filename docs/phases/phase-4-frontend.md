# Fase 4 — Frontend Next.js

## Stack

| Tecnología | Versión | Rol |
|---|---|---|
| Next.js | 16.2.6 | Framework React con App Router |
| React | 19.2.4 | UI library |
| TypeScript | 5.x | Tipado estático |
| Tailwind CSS | 4.x | Utility-first CSS |
| shadcn/ui + @base-ui/react | — | Componentes accesibles |
| lucide-react | 1.14.x | Iconografía |

## Estructura de archivos

```
apps/frontend/
├── proxy.ts                        # Protección de rutas (reemplaza middleware.ts en Next.js 16)
├── app/
│   ├── layout.tsx                  # Root layout (fuente, metadata, globals.css)
│   ├── page.tsx                    # Redirige a /dashboard
│   ├── login/
│   │   └── page.tsx               # Formulario de login
│   └── (dashboard)/
│       ├── layout.tsx             # Layout con Sidebar + Header
│       ├── dashboard/page.tsx     # KPIs y tablas de asistencia
│       ├── employees/page.tsx     # CRUD empleados con paginación
│       ├── documents/page.tsx     # Upload y gestión de PDFs
│       └── chat/page.tsx          # Interfaz de chat con agente RAG
├── components/
│   ├── layout/
│   │   ├── sidebar.tsx            # Navegación lateral
│   │   └── header.tsx             # Header con usuario y logout
│   └── ui/                        # Componentes base shadcn/ui
├── lib/
│   ├── api.ts                     # Cliente API tipado (NestJS + FastAPI)
│   ├── auth.ts                    # Cookie + localStorage session helpers
│   └── utils.ts                   # cn() helper
└── types/
    └── index.ts                   # Tipos TypeScript compartidos
```

## Decisiones clave

### proxy.ts en lugar de middleware.ts

Next.js 16 deprecó `middleware.ts` y lo renombró a `proxy.ts`. La función exportada se llama `proxy` en lugar de `middleware`. El comportamiento es idéntico: corre en el Edge antes del render y puede leer cookies para proteger rutas.

### Sesión dual: cookie + localStorage

- **Cookie `kuaai_token`**: no-httpOnly, leída por `proxy.ts` para redirecciones server-side y por `lib/auth.ts` en el cliente para adjuntar el Bearer token.
- **localStorage `kuaai_user`**: almacena el objeto `AuthUser` (id, email, role) para uso en componentes cliente sin necesitar peticiones adicionales.

### @base-ui/react en lugar de Radix UI

shadcn/ui en este proyecto usa `@base-ui/react` como primitivo. La API difiere de Radix:
- No existe `asChild` — se usa `render={<Button />}` para componer componentes.
- `Dialog.Trigger`, `Dialog.Close`, etc. aceptan `render` prop.

## Flujo de autenticación

```
Usuario → /login → authApi.login() → saveSession(token, user)
                                         ├── cookie kuaai_token (max-age=86400)
                                         └── localStorage kuaai_user

proxy.ts → lee cookie → redirige si no hay token
Header → getUser() → lee localStorage → muestra email/rol
```

## Módulos implementados

### Dashboard (`/dashboard`)
- Carga en paralelo: `today`, `monthlyAverage`, `tardiness`
- 4 KPI cards: empleados activos, presentes, ausentes, promedio mensual
- Tabla de ausentes del día con badge de departamento
- Top 5 tardanzas del mes con conteo

### Empleados (`/employees`)
- Tabla paginada con búsqueda por nombre y filtro por departamento
- Dialog de creación con validación de campos requeridos
- Dialog de edición inline (por fila)
- Botón de desactivación con confirmación

### Documentos (`/documents`)
- Upload a NestJS (`POST /documents/upload`) con `multipart/form-data` — NestJS aplica JWT y hace proxy a FastAPI
- Disparo automático del pipeline RAG (`POST /documents/process`) a través de NestJS
- Badge de estado: READY / PROCESSING / ERROR
- Stepper visual de 4 pasos (Descarga → Extracción → Fragmentación → Embeddings) durante el procesamiento
- Polling automático cada 3 segundos mientras haya documentos en estado `PROCESSING`
- Eliminación con confirmación

### Chat (`/chat`)
- Carga historial al montar desde `GET /agent/history/{userId}`
- Envío con Enter (Shift+Enter = nueva línea)
- Thread persistente: `user-{userId}`
- Scroll automático al último mensaje
- Indicador de "Pensando..." mientras espera respuesta
- Errores del agente mostrados como mensajes del asistente (incluye mensajes de rate limit legibles)

## Manejo de errores de API

`lib/api.ts` parsea tanto `body.message` (NestJS) como `body.detail` (FastAPI) para mostrar mensajes de error descriptivos en lugar de "Error 500" genérico.
