# ADR-006 — ID fijo para el mensaje system del agente

## Fecha
2026-08-21

## Contexto

Al auditar los mecanismos de guardrail y manejo de historial del agente RAG
(`agent_service.py`), se detectó que la función `chat()` reconstruía el
mensaje `system` en cada turno y lo pasaba a `_agent.invoke()` sin un `id`
explícito:

```python
result = _agent.invoke(
    {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
    },
    config=config,
)
```

El agente usa `MemorySaver` como checkpointer de LangGraph, indexado por
`thread_id`. `create_react_agent` administra el estado de mensajes con el
reducer `add_messages`, cuyo comportamiento es: si el mensaje entrante tiene
el mismo `id` que uno ya presente en el estado, lo **reemplaza**; si no,
lo **agrega** como mensaje nuevo.

Como el dict `{"role": "system", "content": system}` no traía `id`,
LangChain le asignaba un UUID nuevo en cada conversión a `SystemMessage`.
Cada turno generaba entonces una copia distinta del system prompt, que se
sumaba al historial acumulado del thread en vez de reemplazar la anterior.

Se verificó el bug con una prueba real de 3 turnos contra el agente
desplegado (mismo `thread_id`, contando `system_messages` en el estado del
checkpointer tras cada turno):

```
Turno 1: total_messages=3  system_messages=1  ids=['68167d5e-...']
Turno 2: total_messages=8  system_messages=2  ids=['68167d5e-...', 'acb52ce8-...']
Turno 3: total_messages=13 system_messages=3  ids=['68167d5e-...', 'acb52ce8-...', 'a86ff11b-...']
```

Esto no rompía la conversación (el LLM tolera varios mensajes `system`),
pero infla el consumo de tokens de forma innecesaria en cada turno adicional,
agravando el problema ya existente de que el historial completo del thread
se reenvía sin ningún mecanismo de recorte (no hay `trim_messages`, resumen
ni límite de turnos en `agent_service.py`). En un free tier de Groq con
límite de 8000 TPM, esta duplicación acelera el agotamiento del rate limit.

## Decisión

Asignar un `id` fijo y estable al mensaje `system` en cada invocación:

```python
{"role": "system", "content": system, "id": "system-prompt"}
```

## Razones

1. **Corrige la causa raíz, no el síntoma.** El problema es que el reducer
   `add_messages` no tiene forma de saber que dos mensajes `system` de
   turnos distintos representan "el mismo" mensaje lógico sin un `id`
   compartido. Fijar el `id` resuelve esto sin tocar la lógica del agente
   ni el checkpointer.
2. **Cambio mínimo.** Una sola línea, sin nuevas dependencias ni cambios de
   arquitectura.
3. **No introduce riesgo de desincronización.** Si en el futuro cambia el
   contenido del `system` (por ejemplo, la fecha interpolada cambia día a
   día), el mismo `id` garantiza que la versión más reciente reemplace a la
   anterior en el estado — no se acumulan versiones viejas del prompt con
   fechas desactualizadas.

## Consecuencias

**Positivas:**
- El historial de un thread contiene una única copia del system prompt,
  siempre actualizada, sin importar cuántos turnos lleve la conversación.
- Reduce el consumo de tokens por turno en conversaciones largas.
- Verificado con prueba real: tras el fix, `system_messages=1` se mantiene
  constante en los 3 turnos de prueba, con el mismo `id` (`"system-prompt"`).

**Negativas / pendientes:**
- Este fix **no resuelve** el problema de fondo de que el resto del
  historial (preguntas, tool calls, resultados de tools, respuestas) sigue
  sin ningún mecanismo de recorte — el historial de un thread activo puede
  seguir creciendo sin límite y consumiendo cada vez más tokens por turno.
  Queda pendiente evaluar `trim_messages`, un resumen periódico del
  historial, o un límite de turnos/tokens por thread.

## Cómo probarlo

```bash
docker compose up -d backend-fastapi
# crear un thread real (conversation_threads) y hacer 3+ llamados a
# agent_service.chat() con el mismo thread_id, inspeccionando
# agent_service._agent.get_state({"configurable": {"thread_id": thread_id}})
# .values["messages"] tras cada turno: la cantidad de mensajes con
# type == "system" debe mantenerse en 1.
```
