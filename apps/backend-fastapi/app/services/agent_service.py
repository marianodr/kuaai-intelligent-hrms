import logging
from datetime import date
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from app.tools.hrms_tools import ALL_TOOLS
from app import database

logger = logging.getLogger(__name__)

_agent = None
_checkpointer = MemorySaver()

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
- Cuando uses la herramienta search_documents, al final de tu respuesta incluí una línea con el formato: "Fuentes: [nombre_documento_1, nombre_documento_2]"
"""


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
    )
    logger.info(f"Agente inicializado con modelo {settings.groq_model} y {len(ALL_TOOLS)} herramientas")


def chat(question: str, user_id: int, thread_id: str) -> str:
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
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ]
        },
        config=config,
    )
    answer = result["messages"][-1].content

    _save_history(user_id, question, answer, thread_id)
    return answer


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
