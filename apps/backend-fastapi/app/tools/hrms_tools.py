import json
import logging
from pydantic import BaseModel
from langchain_core.tools import tool, StructuredTool

from app import database, embeddings as emb_service

logger = logging.getLogger(__name__)


def _rows_to_json(rows) -> str:
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


# ── Tools de un solo parámetro — @tool funciona bien ─────────────────────────

@tool
def search_documents(query: str) -> str:
    """Busca información en los documentos empresariales cargados
    (políticas, reglamentos, manuales). Usar para preguntas sobre
    normativas, procedimientos y reglas de la empresa.
    Parámetro query: la pregunta o término a buscar."""
    embedding = emb_service.get_embedding(query)
    emb_str = emb_service.embedding_to_pg_str(embedding)

    with database.get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT
                dc.content,
                d.name AS document_name,
                ROUND((1 - (dc.embedding <=> %s::vector))::numeric, 3) AS similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'READY'
            ORDER BY dc.embedding <=> %s::vector
            LIMIT 4
            """,
            (emb_str, emb_str),
        )
        rows = cur.fetchall()

    if not rows:
        return "No se encontraron documentos relevantes para la consulta."

    results = [
        {"fragment": r["content"], "documento": r["document_name"], "similitud": float(r["similarity"])}
        for r in rows
    ]
    return json.dumps(results, ensure_ascii=False)


@tool
def get_daily_attendance(date: str) -> str:
    """Retorna la asistencia del día indicado.
    Incluye empleados presentes, ausentes y con tardanza.
    Parámetro date: fecha en formato YYYY-MM-DD (ejemplo: 2024-11-15)."""
    with database.get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT
                e.first_name || ' ' || e.last_name AS nombre,
                e.department AS departamento,
                ar.is_late AS tardanza,
                ar.timestamp::time AS hora_entrada
            FROM attendance_records ar
            JOIN employees e ON ar.employee_id = e.id
            WHERE DATE(ar.timestamp) = %s AND ar.record_type = 'ENTRADA'
            ORDER BY ar.timestamp
            """,
            (date,),
        )
        present = cur.fetchall()

        cur.execute("SELECT count(*) AS total FROM employees WHERE status = 'ACTIVO'")
        total_active = cur.fetchone()["total"]

    late_count = sum(1 for r in present if r["tardanza"])
    result = {
        "fecha": date,
        "total_activos": total_active,
        "presentes": len(present),
        "ausentes": total_active - len(present),
        "tardanzas": late_count,
        "detalle": [dict(r) for r in present],
    }
    return json.dumps(result, ensure_ascii=False, default=str)


@tool
def get_employee_info(query: str) -> str:
    """Busca información de un empleado por nombre, apellido o legajo.
    Retorna datos básicos del perfil.
    Parámetro query: nombre, apellido o número de legajo a buscar."""
    with database.get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT
                id, first_name, last_name, email, legajo,
                department, status, created_at
            FROM employees
            WHERE
                first_name ILIKE %s
                OR last_name ILIKE %s
                OR (first_name || ' ' || last_name) ILIKE %s
                OR legajo ILIKE %s
            ORDER BY last_name, first_name
            LIMIT 5
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"),
        )
        rows = cur.fetchall()

    if not rows:
        return f"No se encontró ningún empleado que coincida con '{query}'."

    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


# ── Tools con múltiples parámetros — StructuredTool + Pydantic ───────────────
# El decorator @tool no genera schemas correctos para múltiples params enteros
# con la versión de langchain-groq/Groq API instalada, causando tool_use_failed.

class _EmployeeAttendanceArgs(BaseModel):
    employee_id: int
    month: int
    year: int


def _get_employee_attendance(employee_id: int, month: int, year: int) -> str:
    with database.get_cursor() as (cur, conn):
        cur.execute(
            "SELECT first_name || ' ' || last_name AS nombre FROM employees WHERE id = %s",
            (employee_id,),
        )
        emp = cur.fetchone()
        if not emp:
            return f"Empleado con ID {employee_id} no encontrado."

        cur.execute(
            """
            SELECT
                record_type,
                is_late,
                auto_generated,
                DATE(timestamp) AS fecha
            FROM attendance_records
            WHERE employee_id = %s
              AND EXTRACT(MONTH FROM timestamp) = %s
              AND EXTRACT(YEAR FROM timestamp) = %s
            ORDER BY timestamp
            """,
            (employee_id, month, year),
        )
        records = cur.fetchall()

    dias_presentes = len({r["fecha"] for r in records if r["record_type"] == "ENTRADA"})
    tardanzas = sum(1 for r in records if r["is_late"])
    salidas_auto = sum(1 for r in records if r["auto_generated"])

    result = {
        "empleado": emp["nombre"],
        "mes": month,
        "anio": year,
        "dias_presentes": dias_presentes,
        "tardanzas": tardanzas,
        "salidas_automaticas": salidas_auto,
        "registros": [dict(r) for r in records],
    }
    return json.dumps(result, ensure_ascii=False, default=str)


get_employee_attendance = StructuredTool.from_function(
    func=_get_employee_attendance,
    name="get_employee_attendance",
    description="Retorna el resumen de asistencias de un empleado en un mes y año específico. "
                "Incluye días presentes, tardanzas y salidas automáticas. "
                "Usar employee_id (obtenido con get_employee_info), month (1-12) y year.",
    args_schema=_EmployeeAttendanceArgs,
)


class _MonthYearArgs(BaseModel):
    month: int
    year: int


def _get_tardiness_report(month: int, year: int) -> str:
    with database.get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT
                e.first_name || ' ' || e.last_name AS nombre,
                e.department AS departamento,
                COUNT(*) AS cantidad_tardanzas
            FROM attendance_records ar
            JOIN employees e ON ar.employee_id = e.id
            WHERE ar.is_late = true
              AND EXTRACT(MONTH FROM ar.timestamp) = %s
              AND EXTRACT(YEAR FROM ar.timestamp) = %s
            GROUP BY e.id, e.first_name, e.last_name, e.department
            ORDER BY cantidad_tardanzas DESC
            """,
            (month, year),
        )
        rows = cur.fetchall()

    result = {
        "mes": month,
        "anio": year,
        "total_empleados_con_tardanzas": len(rows),
        "detalle": [dict(r) for r in rows],
    }
    return json.dumps(result, ensure_ascii=False, default=str)


get_tardiness_report = StructuredTool.from_function(
    func=_get_tardiness_report,
    name="get_tardiness_report",
    description="Retorna lista de empleados con tardanzas en el mes indicado, "
                "ordenados por cantidad de tardanzas. Parámetros: month (1-12) y year.",
    args_schema=_MonthYearArgs,
)


def _get_monthly_summary(month: int, year: int) -> str:
    with database.get_cursor() as (cur, conn):
        cur.execute("SELECT count(*) AS total FROM employees WHERE status = 'ACTIVO'")
        total_active = cur.fetchone()["total"]

        cur.execute(
            """
            SELECT
                DATE(timestamp) AS fecha,
                COUNT(DISTINCT employee_id) AS presentes
            FROM attendance_records
            WHERE record_type = 'ENTRADA'
              AND EXTRACT(MONTH FROM timestamp) = %s
              AND EXTRACT(YEAR FROM timestamp) = %s
            GROUP BY DATE(timestamp)
            ORDER BY fecha
            """,
            (month, year),
        )
        days = cur.fetchall()

        cur.execute(
            """
            SELECT COUNT(*) AS total
            FROM attendance_records
            WHERE is_late = true
              AND EXTRACT(MONTH FROM timestamp) = %s
              AND EXTRACT(YEAR FROM timestamp) = %s
            """,
            (month, year),
        )
        total_tardanzas = cur.fetchone()["total"]

    if not days:
        return json.dumps({"mes": month, "anio": year, "mensaje": "Sin registros para ese período."})

    avg_present = sum(d["presentes"] for d in days) / len(days)
    avg_pct = round((avg_present / total_active * 100), 1) if total_active > 0 else 0

    result = {
        "mes": month,
        "anio": year,
        "total_empleados_activos": total_active,
        "dias_con_registros": len(days),
        "promedio_presentes_por_dia": round(avg_present, 1),
        "porcentaje_asistencia_promedio": avg_pct,
        "total_tardanzas_del_mes": total_tardanzas,
        "detalle_por_dia": [dict(d) for d in days],
    }
    return json.dumps(result, ensure_ascii=False, default=str)


get_monthly_summary = StructuredTool.from_function(
    func=_get_monthly_summary,
    name="get_monthly_summary",
    description="Retorna resumen general de asistencia del mes: porcentaje promedio, "
                "días con registros y total de tardanzas. Parámetros: month (1-12) y year.",
    args_schema=_MonthYearArgs,
)


ALL_TOOLS = [
    search_documents,
    get_daily_attendance,
    get_employee_attendance,
    get_tardiness_report,
    get_monthly_summary,
    get_employee_info,
]
