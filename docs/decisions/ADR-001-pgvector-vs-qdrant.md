# ADR-001 — pgvector vs Qdrant

## Fecha
2026-05-11

## Contexto

El sistema Kuaai requiere almacenar y buscar vectores de embeddings (384 dimensiones, generados por `all-MiniLM-L6-v2`) para el pipeline RAG de documentos empresariales. Se evaluaron dos opciones:

- **pgvector:** extensión de PostgreSQL que agrega el tipo `vector` y operadores de búsqueda por similitud (`<=>`, `<#>`, `<+>`)
- **Qdrant:** base de datos vectorial dedicada, diseñada exclusivamente para búsqueda semántica

El sistema ya requiere PostgreSQL como base de datos relacional para empleados, asistencias y usuarios.

## Decisión

Se usa **pgvector** sobre PostgreSQL 16.

## Razones

1. **Un solo motor de base de datos:** evita operar y mantener un segundo servicio dedicado. Para un MVP con volumen moderado (decenas de documentos), pgvector es más que suficiente.

2. **Queries mixtos sin overhead:** se pueden hacer JOINs directos entre tablas relacionales y vectores en una sola consulta SQL. Ejemplo: filtrar chunks solo de documentos con `status = 'READY'` sin round-trip entre servicios.

3. **Simplicidad de deployment:** un único contenedor Docker (`pgvector/pgvector:pg16`) en lugar de dos. El `docker-compose.yml` ya tiene un servicio menos que mantener.

4. **Persistencia y transacciones:** pgvector hereda todas las garantías ACID de PostgreSQL. Los chunks se insertan en la misma transacción que actualiza el estado del documento.

5. **Escala suficiente para el MVP:** el índice `ivfflat` con `lists=100` soporta eficientemente hasta ~1 millón de vectores. Para una PyME con decenas de documentos, el rendimiento es más que adecuado.

6. **Contexto académico:** el proyecto es un PFG (Proyecto Final de Grado). Reducir la complejidad operacional permite focalizarse en las funcionalidades de valor (RAG, IoT, UX).

## Consecuencias

**Positivas:**
- Un solo servicio de base de datos para toda la persistencia del sistema
- Backup y restore simplificados (un solo `pg_dump`)
- Menor curva de aprendizaje para el mantenimiento futuro

**Negativas:**
- pgvector no tiene las capacidades avanzadas de filtrado y búsqueda aproximada de Qdrant
- Para escalar a millones de vectores o búsquedas de alta concurrencia, habría que migrar a una solución dedicada
- El índice `ivfflat` requiere re-indexación manual si el volumen crece significativamente (`VACUUM` + recrear índice)

**Revisión futura:** si el sistema escala a múltiples empresas (SaaS) con miles de documentos por cliente, evaluar migración a Qdrant o PGVector en una instancia dedicada.
