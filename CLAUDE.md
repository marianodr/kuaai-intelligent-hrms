# CLAUDE.md — Instrucciones para Claude Code

## Contexto del proyecto
Kuaai es un MVP de HRMS inteligente. Lee PLAN.md para
entender la arquitectura completa antes de implementar.

## Reglas generales
- Antes de implementar cualquier cosa, leé PLAN.md
- Nunca tomes decisiones arquitectónicas sin consultarme
- Si encontrás un problema, explicá las opciones antes de elegir
- Siempre implementá manejo de errores
- Usá TypeScript estricto en NestJS y Next.js
- Usá type hints en todo el código Python

## Documentación — obligatorio al terminar cada fase
Al completar cada fase, generá el documento correspondiente
en docs/phases/ con esta estructura:

### Estructura del documento de fase
- Lo que se implementó
- Decisiones técnicas tomadas
- Estructura de archivos creados
- Cómo probarlo
- Problemas encontrados y soluciones
- Pendientes para fases siguientes

## Architecture Decision Records (ADR)
Cuando se tome una decisión técnica importante, generá
un ADR en docs/decisions/ con este formato:

### Estructura del ADR
- Fecha
- Contexto
- Decisión
- Razones
- Consecuencias

## Convenciones de código

### NestJS
- Módulos por dominio: auth, employees, attendance, documents
- DTOs para todas las requests y responses
- Guards para autenticación y roles
- Services para lógica de negocio
- Controllers solo para routing

### FastAPI
- Routers por dominio: documents, agent
- Pydantic models para todas las requests y responses
- Services para lógica de negocio
- Type hints obligatorios

### Next.js
- App Router
- Server Components por defecto
- Client Components solo cuando sea necesario
- shadcn/ui para componentes de UI

## Estructura de commits
Usar conventional commits:
- feat: nueva funcionalidad
- fix: corrección de bug
- docs: documentación
- chore: configuración

## Variables de entorno
Nunca hardcodear valores. Siempre usar variables
de entorno definidas en .env.example

## Docker
Cada servicio debe tener su propio Dockerfile.
El docker-compose.yml está en la raíz del monorepo.

## Base de datos
- Usar migraciones para todos los cambios de esquema
- Nunca modificar tablas directamente en producción
- Seeders para datos iniciales de prueba

## Orden de implementación
Seguir estrictamente las fases definidas en PLAN.md.
No avanzar a la siguiente fase sin confirmar con el usuario.