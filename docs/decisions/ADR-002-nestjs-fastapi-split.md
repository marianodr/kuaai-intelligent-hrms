# ADR-002 — Separación NestJS / FastAPI

## Fecha
2026-05-11

## Contexto

El sistema necesita dos tipos de capacidades muy distintas:

1. **Dominio HRMS:** API REST tipada, autenticación JWT con roles, CRUD con validaciones, MQTT, cron jobs → ecosistema backend empresarial clásico.
2. **Dominio IA:** embeddings con SentenceTransformers, procesamiento de PDFs con Docling, agente LangChain, integración con Groq → ecosistema Python/ML.

La alternativa sería un único backend en un lenguaje que cubra ambos dominios.

## Decisión

Se usa **NestJS (TypeScript)** para el dominio HRMS y **FastAPI (Python)** para el dominio IA, con comunicación REST entre ellos orquestada por el frontend Next.js.

## Razones

1. **Python domina el ecosistema IA:** las librerías clave del proyecto (`langchain`, `langgraph`, `sentence-transformers`, `docling`) son exclusivamente Python. Implementarlas en Node.js implicaría wrappers, bindings nativos o llamadas a procesos externos, añadiendo complejidad sin beneficio.

2. **TypeScript domina el ecosistema backend empresarial:** NestJS con TypeORM, Passport, class-validator y `@nestjs/schedule` provee un framework maduro para APIs tipadas con guards, pipes, decoradores e inyección de dependencias. Replicar esto en FastAPI para el dominio HRMS sería innecesariamente complejo.

3. **Separación de responsabilidades clara:** cada servicio tiene un único dominio, un Dockerfile independiente y puede evolucionar por separado. El backend IA puede incorporar nuevos modelos o herramientas sin afectar la lógica de RRHH.

4. **Escalabilidad independiente:** en el futuro, el backend FastAPI (computacionalmente intensivo por embeddings) puede escalarse con más réplicas sin afectar el backend NestJS.

5. **Patrón habitual en sistemas con componentes IA:** la separación "backend de negocio en lenguaje tipado" + "backend IA en Python" es un patrón ampliamente adoptado en la industria.

## Consecuencias

**Positivas:**
- Cada equipo/persona puede especializarse en su dominio
- Tests independientes por servicio
- Deployments independientes
- Mejor rendimiento: cada servicio usa el runtime óptimo para su carga

**Negativas:**
- Dos stacks tecnológicos que mantener (Node.js + Python)
- La comunicación entre servicios introduce latencia de red (aunque mínima en la misma red Docker)
- El frontend necesita conocer dos URLs de API (`NEXT_PUBLIC_API_URL` y `NEXT_PUBLIC_AI_API_URL`)
- Complejidad adicional en el monorepo: dos `package.json`, dos `requirements.txt`, dos Dockerfiles

**Interfaz de comunicación:**
- NestJS llama a FastAPI para registrar y procesar documentos (`POST /documents/register`, `POST /documents/process`)
- El frontend Next.js llama directamente a FastAPI para el chat del agente (`POST /agent/chat`)
