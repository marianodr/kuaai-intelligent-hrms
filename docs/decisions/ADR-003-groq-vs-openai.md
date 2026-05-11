# ADR-003 — Groq vs OpenAI API

## Fecha
2026-05-11

## Contexto

El agente RAG requiere un LLM (Large Language Model) con capacidad de **tool calling** para ejecutar las 6 herramientas de Kuaai. Se evaluaron dos opciones principales:

- **Groq API con Llama 3.1 8B Instant:** proveedor de inferencia ultra-rápida para modelos open source. Ofrece un tier gratuito con límites generosos.
- **OpenAI API con GPT-4o / GPT-4o-mini:** LLMs propietarios de OpenAI, líderes en benchmark pero con costo por token.

También se consideró **Ollama local** (Llama 3.1 8B corriendo en la máquina del servidor) como alternativa sin dependencia externa.

## Decisión

Se usa **Groq API con el modelo `llama-3.1-8b-instant`**.

## Razones

1. **Tier gratuito suficiente para MVP:** Groq ofrece acceso gratuito con límites de requests por minuto/día que son más que suficientes para un MVP académico y demostraciones.

2. **Velocidad de inferencia:** Groq usa hardware especializado (LPU — Language Processing Unit) que ofrece velocidades de inferencia significativamente más rápidas que OpenAI para el mismo modelo. Esto mejora la experiencia de usuario en el chat.

3. **Tool calling nativo:** `llama-3.1-8b-instant` soporta function/tool calling de forma nativa a través de la API de Groq, requisito indispensable para el agente ReAct.

4. **Sin costo en desarrollo:** permite iterar sobre el prompt del sistema y las herramientas sin preocuparse por el costo por token durante el desarrollo y las pruebas.

5. **Llama 3.1 8B es suficiente para el caso de uso:** las consultas de RRHH (asistencias, empleados, documentos cortos de empresa) no requieren capacidades de razonamiento extremadamente complejas. El modelo 8B maneja correctamente la selección de herramientas y la generación de respuestas en español.

6. **`langchain-groq` oficial:** Groq tiene integración oficial con LangChain (`langchain-groq`), lo que facilita el uso con `create_react_agent`.

## Consecuencias

**Positivas:**
- Sin costo durante desarrollo y MVP
- Alta velocidad de respuesta (experiencia de chat fluida)
- Modelo open source auditabledable y reproducible
- Compatible con langchain-groq sin adaptadores

**Negativas:**
- Dependencia de un servicio externo: si Groq tiene downtime, el agente no funciona
- Los límites del tier gratuito pueden ser restrictivos en producción con múltiples usuarios simultáneos
- GPT-4o tendría mejor razonamiento para consultas ambiguas o complejas
- El modelo 8B puede cometer errores en selección de herramienta ante preguntas ambiguas

**Migración futura:**
- Al escalar a producción real, evaluar **Ollama local** con Llama 3.1 para privacidad total de los datos (mencionado en el roadmap del PLAN.md)
- Alternativamente, Groq ofrece planes de pago con límites más altos
- La integración LangChain permite cambiar el LLM con una sola línea: `ChatGroq(...)` → `ChatOpenAI(...)` o `ChatOllama(...)`
