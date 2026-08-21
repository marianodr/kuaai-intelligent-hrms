#!/usr/bin/env python3
# =============================================================================
# Kuaai HRMS — Verificación tool-por-tool del agente RAG
#
# A diferencia de scripts/test-e2e.sh (sección 6), que solo valida que
# POST /agent/chat devuelva un `answer` no vacío, este script verifica que
# CADA una de las 6 herramientas del agente:
#   (a) se invoque cuando corresponde — y no otra, ni ninguna
#   (b) reciba argumentos razonables para la pregunta hecha
#   (c) su resultado real se vea reflejado en la respuesta final del agente
#       (y no una respuesta genérica que lo ignora)
#
# Requiere el campo `tool_calls` en la respuesta de POST /agent/chat
# (apps/backend-fastapi/app/routers/agent.py + app/services/agent_service.py),
# que expone los mensajes intermedios que create_react_agent ya arma
# internamente (AIMessage.tool_calls + ToolMessage.content).
#
# Uso: python3 scripts/test-agent-tools.py
# Requiere: Python 3.10+ (solo stdlib), stack levantado (docker compose up).
# =============================================================================
import json
import sys
import time
import urllib.error
import urllib.request

NEST = "http://localhost:3001"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def bold(msg):
    print(f"\n{BOLD}{msg}{RESET}")


def http(method, url, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"detail": raw.decode(errors="replace")}


def login():
    status, body = http(
        "POST", f"{NEST}/auth/login",
        body={"email": "admin@kuaai.com", "password": "admin123"},
    )
    if status != 201 and status != 200:
        print(f"{RED}No se pudo hacer login (status {status}): {body}{RESET}")
        sys.exit(1)
    return body["access_token"], body["user"]["id"]


def new_thread(token, user_id, name):
    status, body = http(
        "POST", f"{NEST}/threads", token=token,
        body={"user_id": user_id, "name": name},
    )
    if status not in (200, 201):
        raise RuntimeError(f"No se pudo crear thread: {status} {body}")
    return body["id"]


def ask(token, user_id, thread_id, question, retries=3):
    for attempt in range(retries):
        status, body = http(
            "POST", f"{NEST}/agent/chat", token=token,
            body={"question": question, "user_id": user_id, "thread_id": thread_id},
        )
        detail = body.get("detail", "") if isinstance(body, dict) else ""
        if isinstance(detail, str) and ("Límite" in detail or "rate_limit" in detail.lower()):
            wait = 15 * (attempt + 1)
            print(f"  {YELLOW}⚠ Rate limit de Groq, esperando {wait}s (intento {attempt + 1}/{retries})...{RESET}")
            time.sleep(wait)
            continue
        return status, body
    return status, body


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def tool_names(tool_calls):
    return [tc["tool"] for tc in tool_calls]


def find_calls(tool_calls, name):
    return [tc for tc in tool_calls if tc["tool"] == name]


# ─────────────────────────────────────────────────────────────────────────
# Casos de prueba: uno por herramienta, con datos verificados contra la BD
# (ver ground truth consultado directamente vía psql antes de escribir esto).
# ─────────────────────────────────────────────────────────────────────────

def check_search_documents(tc, answer):
    result = tc["result"] or ""
    args_ok = bool(tc["args"].get("query")) and len(tc["args"]["query"]) > 3
    found_real_doc = "Fuente:" in result and "No se encontraron documentos" not in result
    generic_phrases = ["no cuento con", "no tengo información", "no encontré información"]
    answer_ignores_result = any(p in answer.lower() for p in generic_phrases)
    result_applied = found_real_doc and not answer_ignores_result and len(answer) > 40
    return args_ok, result_applied, f"result contiene 'Fuente:'={found_real_doc}"


def check_get_daily_attendance(tc, answer):
    args_ok = tc["args"].get("date") == "2026-08-14"
    try:
        data = json.loads(tc["result"])
    except (TypeError, json.JSONDecodeError):
        return args_ok, False, "no se pudo parsear result como JSON"
    # Ground truth (psql, 2026-08-14): 8 activos, 1 tardanza (Roberto Torres)
    tardanzas = data.get("tardanzas")
    result_applied = (
        str(tardanzas) in answer
        and ("Roberto Torres" in answer or "Torres" in answer)
    )
    return args_ok, result_applied, f"tardanzas={tardanzas}, esperado=1 (Roberto Torres)"


def check_get_employee_attendance(tc, answer):
    a = tc["args"]
    args_ok = (
        as_int(a.get("employee_id")) == 3
        and as_int(a.get("month")) == 8
        and as_int(a.get("year")) == 2026
    )
    try:
        data = json.loads(tc["result"])
    except (TypeError, json.JSONDecodeError):
        return args_ok, False, "no se pudo parsear result como JSON"
    # Ground truth (psql): Pedro Ramírez, agosto 2026 → 1 tardanza, 9 días presentes
    tardanzas = data.get("tardanzas")
    result_applied = str(tardanzas) in answer
    return args_ok, result_applied, f"tardanzas={tardanzas}, esperado=1"


def check_get_tardiness_report(tc, answer):
    a = tc["args"]
    args_ok = as_int(a.get("month")) == 8 and as_int(a.get("year")) == 2026
    try:
        data = json.loads(tc["result"])
    except (TypeError, json.JSONDecodeError):
        return args_ok, False, "no se pudo parsear result como JSON"
    # Ground truth (psql, agosto 2026): top = Carlos Martínez con 3 tardanzas
    detalle = data.get("detalle", [])
    top = detalle[0]["nombre"] if detalle else None
    result_applied = top is not None and "Carlos" in answer and "Martínez" in answer
    return args_ok, result_applied, f"top tardanzas en result={top}, esperado=Carlos Martínez"


def check_get_monthly_summary(tc, answer):
    a = tc["args"]
    args_ok = as_int(a.get("month")) == 8 and as_int(a.get("year")) == 2026
    try:
        data = json.loads(tc["result"])
    except (TypeError, json.JSONDecodeError):
        return args_ok, False, "no se pudo parsear result como JSON"
    pct = data.get("porcentaje_asistencia_promedio")
    pct_int = str(int(pct)) if isinstance(pct, (int, float)) else None
    result_applied = pct is not None and (str(pct) in answer or (pct_int and pct_int in answer))
    return args_ok, result_applied, f"porcentaje_asistencia_promedio={pct}"


def check_get_employee_info(tc, answer):
    q = (tc["args"].get("query") or "").lower()
    args_ok = "juan" in q or "garcía" in q or "garcia" in q
    result = tc["result"] or ""
    found = "EMP-001" in result
    result_applied = found and ("EMP-001" in answer or "Administración" in answer)
    return args_ok, result_applied, f"EMP-001 en result={found}"


TESTS = [
    {
        "tool": "search_documents",
        "question": "¿Cuál es la política de asistencia y horarios de la empresa?",
        "allowed_extra": [],
        "checker": check_search_documents,
    },
    {
        "tool": "get_daily_attendance",
        "question": "¿Cómo fue la asistencia del 14 de agosto de 2026? ¿Quién llegó tarde ese día?",
        "allowed_extra": [],
        "checker": check_get_daily_attendance,
    },
    {
        "tool": "get_employee_attendance",
        "question": "¿Cuántas tardanzas tuvo Pedro Ramírez en agosto de 2026?",
        "allowed_extra": ["get_employee_info"],
        "checker": check_get_employee_attendance,
    },
    {
        "tool": "get_tardiness_report",
        "question": "¿Qué empleados tuvieron tardanzas en agosto de 2026 y cuántas cada uno?",
        "allowed_extra": [],
        "checker": check_get_tardiness_report,
    },
    {
        "tool": "get_monthly_summary",
        "question": "Dame un resumen general de la asistencia de agosto de 2026",
        "allowed_extra": [],
        "checker": check_get_monthly_summary,
    },
    {
        "tool": "get_employee_info",
        "question": "Buscame los datos del empleado Juan García",
        "allowed_extra": [],
        "checker": check_get_employee_info,
    },
]


def run():
    bold("Verificación tool-por-tool del agente RAG (6 herramientas)")
    token, user_id = login()
    print(f"  Login OK (user_id={user_id})")

    rows = []
    created_threads = []
    for i, t in enumerate(TESTS):
        tool = t["tool"]
        print(f"\n{BOLD}[{i + 1}/6] {tool}{RESET}")
        print(f"  Pregunta: {t['question']!r}")

        thread_id = new_thread(token, user_id, f"test-tool-{tool}")
        created_threads.append(thread_id)
        status, body = ask(token, user_id, thread_id, t["question"])

        if status not in (200, 201) or "tool_calls" not in body:
            print(f"  {RED}✗ Error o rate limit persistente: {body}{RESET}")
            rows.append((tool, False, False, False, "sin respuesta válida / rate limit"))
            continue

        answer = body.get("answer", "")
        tool_calls = body.get("tool_calls", [])
        names = tool_names(tool_calls)
        print(f"  Herramientas invocadas: {names or '(ninguna)'}")

        expected_calls = find_calls(tool_calls, tool)
        allowed = {tool, *t["allowed_extra"]}
        unexpected = [n for n in names if n not in allowed]

        invoked_ok = bool(expected_calls) and not unexpected
        if not expected_calls:
            note_a = f"NO invocó {tool}"
        elif unexpected:
            note_a = f"invocó herramienta(s) inesperada(s): {unexpected}"
        else:
            note_a = "OK"

        if expected_calls:
            args_ok, result_applied, note_c = t["checker"](expected_calls[0], answer)
        else:
            args_ok, result_applied, note_c = False, False, "n/a (no se invocó la tool)"

        rows.append((tool, invoked_ok, args_ok, result_applied, f"{note_a} | {note_c}"))

        print(f"  Tool invocada correctamente: {mark(invoked_ok)} ({note_a})")
        print(f"  Argumentos OK: {mark(args_ok)}")
        print(f"  Resultado reflejado en respuesta: {mark(result_applied)} ({note_c})")
        print(f"  Respuesta del agente: {answer[:200]}{'...' if len(answer) > 200 else ''}")

        time.sleep(3)  # margen para no pegarle al rate limit de Groq entre preguntas

    # ─── Cleanup — eliminar hilos de prueba ────────────────────────────────
    bold("Cleanup")
    deleted = 0
    for tid in created_threads:
        status, _ = http("DELETE", f"{NEST}/threads/{tid}", token=token)
        if status in (200, 201, 204):
            deleted += 1
    print(f"  Hilos de prueba eliminados ({deleted}/{len(created_threads)})")

    # ─── Resumen tipo tabla ───────────────────────────────────────────────
    bold("Resumen")
    header = f"{'herramienta':<26} | {'invocada':<9} | {'args OK':<8} | {'resultado aplicado':<19}"
    print(header)
    print("-" * len(header))
    fail_count = 0
    for tool, invoked_ok, args_ok, result_applied, _note in rows:
        if not (invoked_ok and args_ok and result_applied):
            fail_count += 1
        print(
            f"{tool:<26} | {mark(invoked_ok):<9} | {mark(args_ok):<8} | {mark(result_applied):<19}"
        )

    print()
    total = len(rows)
    passed = total - fail_count
    if fail_count == 0:
        print(f"{GREEN}Todas las herramientas ({total}/{total}) pasaron las 3 dimensiones.{RESET}")
    else:
        print(f"{RED}{fail_count}/{total} herramienta(s) fallaron en al menos una dimensión.{RESET}")
        print("\nDetalle de notas por herramienta:")
        for tool, invoked_ok, args_ok, result_applied, note in rows:
            if not (invoked_ok and args_ok and result_applied):
                print(f"  - {tool}: {note}")

    sys.exit(fail_count)


def mark(ok):
    return f"{GREEN}✓ si{RESET}" if ok else f"{RED}✗ no{RESET}"


if __name__ == "__main__":
    run()
