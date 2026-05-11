import logging
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from app.tools.hrms_tools import ALL_TOOLS
from app import database

logger = logging.getLogger(__name__)

_agent = None
_checkpointer = MemorySaver()

SYSTEM_PROMPT = """Eres Kuaai, un asistente inteligente de Recursos Humanos para una empresa.
Tienes acceso a herramientas para consultar información sobre empleados, asistencias y documentos empresariales.

Reglas:
- Responde SIEMPRE en español
- Sé conciso y directo
- Si necesitas información específica (fechas, IDs), solicitala al usuario
- Para consultas sobre documentos empresariales, usa search_documents
- Para consultas sobre asistencia, usa las herramientas de asistencia correspondientes
- Si no tienes información suficiente, dilo claramente
"""


def init_agent(settings) -> None:
    global _agent
    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
    )
    _agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        checkpointer=_checkpointer,
        prompt=SYSTEM_PROMPT,
    )
    logger.info(f"Agente inicializado con modelo {settings.groq_model} y {len(ALL_TOOLS)} herramientas")


def chat(question: str, user_id: int, thread_id: str) -> str:
    """Invoca el agente y persiste el intercambio en chat_history."""
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 15,
    }

    result = _agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config=config,
    )
    answer = result["messages"][-1].content

    _save_history(user_id, question, answer)
    return answer


def _save_history(user_id: int, question: str, answer: str) -> None:
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s)",
            (user_id, "user", question),
        )
        cur.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s)",
            (user_id, "assistant", answer),
        )
        conn.commit()


def get_history(user_id: int, limit: int = 50) -> list[dict]:
    with database.get_cursor() as (cur, conn):
        cur.execute(
            """SELECT role, content, created_at
               FROM chat_history
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (user_id, limit),
        )
        rows = cur.fetchall()
    return [dict(r) for r in reversed(rows)]
