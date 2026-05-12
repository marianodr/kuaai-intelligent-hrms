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
Hoy es {today}. Usa esta fecha como referencia cuando el usuario diga "hoy", "este mes" o "el mes actual".

## Herramientas disponibles y cuándo usarlas

- **search_documents**: para preguntas sobre políticas, reglamentos, procedimientos, beneficios y cualquier documento empresarial cargado en el sistema.
- **get_daily_attendance**: para saber quiénes vinieron o faltaron un día concreto. Parámetro: fecha YYYY-MM-DD.
- **get_employee_attendance**: para el historial de asistencia de un empleado en un mes/año. Necesita el ID numérico del empleado.
- **get_tardiness_report**: para el reporte de tardanzas del mes. Devuelve los empleados ordenados por cantidad de tardanzas.
- **get_monthly_summary**: para el porcentaje de asistencia promedio de un mes completo.
- **get_employee_info**: para buscar datos de un empleado por nombre, apellido o legajo. Usar primero para obtener el ID antes de llamar a get_employee_attendance.

## Reglas de respuesta

- Responde SIEMPRE en español, de forma clara y concisa.
- Cuando respondas con listas de empleados, usa formato de lista con nombre, departamento y datos relevantes.
- Si el usuario pide datos de un mes sin especificar el año, asumir el año actual ({year}).
- Si necesitás el ID de un empleado para otra herramienta, usá primero get_employee_info.
- Si no encontrás información relevante, decilo claramente y sugerí cómo reformular la consulta.
- No inventes datos: solo informa lo que obtuviste de las herramientas.
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
    )
    logger.info(f"Agente inicializado con modelo {settings.groq_model} y {len(ALL_TOOLS)} herramientas")


def chat(question: str, user_id: int, thread_id: str) -> str:
    """Invoca el agente y persiste el intercambio en chat_history."""
    today = date.today()
    system = SYSTEM_PROMPT.format(today=today.isoformat(), year=today.year)

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 15,
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
