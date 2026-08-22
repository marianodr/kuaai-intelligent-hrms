import logging
from datetime import date
from langchain_core.messages import HumanMessage, trim_messages
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from app.tools.hrms_tools import ALL_TOOLS
from app import database

logger = logging.getLogger(__name__)

_agent = None
_checkpointer = MemorySaver()

# Cantidad de turnos (preguntas del usuario) de conversación a conservar en
# el contexto enviado al LLM. Ajustable: Groq limita a 8000 TPM en el free
# tier y sin recorte el contexto de un thread activo crece sin límite turno
# tras turno (ver ADR-006).
MAX_HISTORY_TURNS = 5

SYSTEM_PROMPT = """Eres Kuaai, el asistente inteligente de Recursos Humanos de la empresa.
Hoy es {today}. Usa esta fecha cuando el usuario diga "hoy", "este mes" o "el mes actual".
Si el usuario menciona un mes sin especificar año, asumí el año {year}.

Tenés herramientas para consultar documentos empresariales, asistencia diaria y mensual, información de empleados y reportes de tardanzas. Usá las herramientas antes de responder.

Reglas:
- Respondé SIEMPRE en español, de forma clara y concisa.
- Para consultar asistencia de un empleado específico, primero obtené su ID buscando su información.
- Presentá listas con nombre, departamento y datos relevantes.
- No inventes datos: solo informá lo que obtuviste de las herramientas.
- Si no encontrás información relevante, decilo claramente.
- Si una herramienta devuelve un resultado vacío o "no encontrado", informalo
  directamente al usuario en tu respuesta. No vuelvas a invocar la misma
  herramienta con los mismos argumentos esperando un resultado distinto.
"""


def _count_turns(messages: list) -> int:
    """token_counter de trim_messages: en vez de contar tokens, cuenta
    turnos (mensajes del usuario) en la lista acumulada que va evaluando."""
    return sum(1 for m in messages if isinstance(m, HumanMessage))


def _trim_history(state: dict) -> dict:
    """pre_model_hook: recorta lo que se envía al LLM a system prompt (una
    sola copia) + los últimos MAX_HISTORY_TURNS turnos. No modifica el
    estado persistido del checkpointer (se devuelve vía llm_input_messages),
    así el historial completo sigue disponible en chat_history/get_state."""
    trimmed = trim_messages(
        state["messages"],
        max_tokens=MAX_HISTORY_TURNS,
        token_counter=_count_turns,
        strategy="last",
        start_on="human",
        include_system=True,
    )
    return {"llm_input_messages": trimmed}


def init_agent(settings) -> None:
    global _agent
    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
        max_retries=0,
    )
    _agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        checkpointer=_checkpointer,
        pre_model_hook=_trim_history,
    )
    logger.info(f"Agente inicializado con modelo {settings.groq_model} y {len(ALL_TOOLS)} herramientas")


def _extract_tool_calls(messages: list) -> list[dict]:
    """Reconstruye qué herramientas invocó el agente en esta corrida a partir
    de los mensajes intermedios que ya arma create_react_agent (AIMessage con
    tool_calls + ToolMessage con el resultado). No cambia la lógica del
    agente: solo lee estado que LangGraph ya mantiene internamente."""
    results_by_call_id = {
        msg.tool_call_id: msg.content
        for msg in messages
        if getattr(msg, "type", None) == "tool"
    }

    tool_calls = []
    for msg in messages:
        if getattr(msg, "type", None) != "ai":
            continue
        for tc in getattr(msg, "tool_calls", None) or []:
            tool_calls.append(
                {
                    "tool": tc["name"],
                    "args": tc["args"],
                    "result": results_by_call_id.get(tc["id"]),
                }
            )
    return tool_calls


def chat(question: str, user_id: int, thread_id: str) -> dict:
    """Invoca el agente y persiste el intercambio en chat_history."""
    today = date.today()
    system = SYSTEM_PROMPT.format(today=today.isoformat(), year=today.year)

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25,
    }

    result = _agent.invoke(
        {
            "messages": [
                {"role": "system", "content": system, "id": "system-prompt"},
                {"role": "user", "content": question},
            ]
        },
        config=config,
    )
    answer = result["messages"][-1].content
    tool_calls = _extract_tool_calls(result["messages"])

    _save_history(user_id, question, answer, thread_id)
    return {"answer": answer, "tool_calls": tool_calls}


def _save_history(user_id: int, question: str, answer: str, thread_id: str | None = None) -> None:
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute(
            "INSERT INTO chat_history (user_id, role, content, thread_id) VALUES (%s, %s, %s, %s)",
            (user_id, "user", question, thread_id),
        )
        cur.execute(
            "INSERT INTO chat_history (user_id, role, content, thread_id) VALUES (%s, %s, %s, %s)",
            (user_id, "assistant", answer, thread_id),
        )
        if thread_id:
            cur.execute(
                "UPDATE conversation_threads SET last_message_at = NOW() WHERE id = %s",
                (thread_id,),
            )
        conn.commit()


def get_history(user_id: int, limit: int = 50, thread_id: str | None = None) -> list[dict]:
    with database.get_cursor() as (cur, conn):
        # Se ordena por id (no solo por created_at): el mensaje del usuario y
        # la respuesta del agente se insertan en la misma transacción, y
        # NOW() devuelve la hora de inicio de la transacción (igual para
        # ambas filas), por lo que created_at por sí solo no alcanza para
        # desempatar el orden cronológico real.
        if thread_id:
            cur.execute(
                """SELECT role, content, created_at
                   FROM chat_history
                   WHERE user_id = %s AND thread_id = %s
                   ORDER BY id DESC
                   LIMIT %s""",
                (user_id, thread_id, limit),
            )
        else:
            cur.execute(
                """SELECT role, content, created_at
                   FROM chat_history
                   WHERE user_id = %s
                   ORDER BY id DESC
                   LIMIT %s""",
                (user_id, limit),
            )
        rows = cur.fetchall()
    return [dict(r) for r in reversed(rows)]
