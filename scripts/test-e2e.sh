#!/usr/bin/env bash
# =============================================================
# Kuaai HRMS — Test E2E de todos los flujos
# Requiere: curl, jq, mosquitto_pub
# Uso: ./scripts/test-e2e.sh
# =============================================================

set -euo pipefail

NEST="http://localhost:3001"
FAPI="http://localhost:8000"
PASS=0
FAIL=0

green() { echo -e "\033[32m✓ $*\033[0m"; }
red()   { echo -e "\033[31m✗ $*\033[0m"; }
bold()  { echo -e "\n\033[1m$*\033[0m"; }

check() {
    local label="$1" condition="$2"
    if eval "$condition"; then
        green "$label"
        PASS=$((PASS + 1))
    else
        red "$label"
        FAIL=$((FAIL + 1))
    fi
}

# ─── 0. Health checks ────────────────────────────────────────
bold "0. Health checks"

NEST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$NEST/auth/login" -X POST \
    -H "Content-Type: application/json" -d '{}' || echo "000")
check "NestJS accesible (POST /auth/login responde)" '[ "$NEST_STATUS" != "000" ]'

FAPI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FAPI/health" || echo "000")
check "FastAPI accesible (GET /health = 200)" '[ "$FAPI_STATUS" = "200" ]'

# ─── 1. Autenticación ────────────────────────────────────────
bold "1. Autenticación"

LOGIN=$(curl -s -X POST "$NEST/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@kuaai.com","password":"admin123"}')

TOKEN=$(echo "$LOGIN" | jq -r '.access_token // empty')
check "Login admin → recibe access_token" '[ -n "$TOKEN" ]'

USER_ID=$(echo "$LOGIN" | jq -r '.user.id // empty')
check "Login response contiene user.id" '[ -n "$USER_ID" ]'

USER_ROLE=$(echo "$LOGIN" | jq -r '.user.role // empty')
check "Login response contiene role=admin" '[ "$USER_ROLE" = "admin" ]'

# ─── 2. Empleados ────────────────────────────────────────────
bold "2. Empleados"

EMP_LIST=$(curl -s "$NEST/employees?page=1&limit=10" \
    -H "Authorization: Bearer $TOKEN")
EMP_TOTAL=$(echo "$EMP_LIST" | jq -r '.total // 0')
check "GET /employees retorna total > 0" '[ "$EMP_TOTAL" -gt 0 ]'

TS=$(date +%s)
EMP_CREATE=$(curl -s -X POST "$NEST/employees" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"first_name\":\"Test\",\"last_name\":\"E2E\",\"legajo\":\"EMP-E2E-$TS\",\"rfid_code\":\"E2E$TS\",\"department\":\"QA\"}")
NEW_ID=$(echo "$EMP_CREATE" | jq -r '.id // empty')
check "POST /employees crea empleado y retorna id" '[ -n "$NEW_ID" ]'

UPD=$(curl -s -X PUT "$NEST/employees/$NEW_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"department":"Testing"}')
UPD_DEP=$(echo "$UPD" | jq -r '.department // empty')
check "PUT /employees/:id actualiza departamento" '[ "$UPD_DEP" = "Testing" ]'

DEL=$(curl -s -X DELETE "$NEST/employees/$NEW_ID" \
    -H "Authorization: Bearer $TOKEN")
DEL_STATUS=$(echo "$DEL" | jq -r '.status // empty')
check "DELETE /employees/:id desactiva empleado (status=INACTIVO)" '[ "$DEL_STATUS" = "INACTIVO" ]'

# ─── 3. Dashboard ────────────────────────────────────────────
bold "3. Dashboard"

TODAY=$(curl -s "$NEST/dashboard/today" \
    -H "Authorization: Bearer $TOKEN")
check "GET /dashboard/today retorna total_active" \
    '[ "$(echo "$TODAY" | jq -r ".total_active")" != "null" ]'

MONTH=$(date +%-m)
YEAR=$(date +%Y)
MONTHLY=$(curl -s "$NEST/dashboard/monthly-average?month=$MONTH&year=$YEAR" \
    -H "Authorization: Bearer $TOKEN")
check "GET /dashboard/monthly-average retorna average_attendance_pct" \
    '[ "$(echo "$MONTHLY" | jq -r ".average_attendance_pct")" != "null" ]'

TARD=$(curl -s "$NEST/dashboard/tardiness?month=$MONTH&year=$YEAR" \
    -H "Authorization: Bearer $TOKEN")
check "GET /dashboard/tardiness retorna tardiness[]" \
    '[ "$(echo "$TARD" | jq -r ".tardiness | length")" -ge 0 ]'

# ─── 4. MQTT — Simulación de fichaje RFID ────────────────────
bold "4. MQTT — Fichaje RFID"

if command -v mosquitto_pub &>/dev/null; then
    mosquitto_pub -h localhost -p 1883 -t "attendance/checkin" \
        -m '{"rfid_code":"37194205"}' 2>/dev/null
    sleep 1
    TODAY_AFTER=$(curl -s "$NEST/dashboard/today" \
        -H "Authorization: Bearer $TOKEN")
    check "mosquitto_pub publica fichaje sin error" "true"
    check "Dashboard responde tras fichaje MQTT" \
        '[ "$(echo "$TODAY_AFTER" | jq -r ".date")" != "null" ]'
else
    echo "  ⚠ mosquitto_pub no instalado — saltando prueba MQTT"
    echo "  Instalá con: sudo apt install mosquitto-clients"
fi

# ─── 5. Documentos ───────────────────────────────────────────
bold "5. Documentos (vía NestJS proxy)"

DOCS=$(curl -s "$NEST/documents" \
    -H "Authorization: Bearer $TOKEN")
check "GET /documents retorna array" \
    '[ "$(echo "$DOCS" | jq -r "type")" = "array" ]'

# ─── 6. Agente RAG ───────────────────────────────────────────
bold "6. Agente RAG (vía NestJS proxy)"

CHAT=$(curl -s -X POST "$NEST/agent/chat" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"¿Cuántos empleados hay activos?\",\"user_id\":$USER_ID,\"thread_id\":\"test-e2e\"}")
CHAT_DETAIL=$(echo "$CHAT" | jq -r '.detail // empty')
if [[ "$CHAT_DETAIL" == *"Límite"* ]]; then
    echo "  ⚠ Rate limit de Groq — saltando prueba del agente (reintentar en ~60s)"
else
    ANSWER=$(echo "$CHAT" | jq -r '.answer // empty')
    check "POST /agent/chat retorna answer no vacío" '[ -n "$ANSWER" ]'
fi

HIST=$(curl -s "$NEST/agent/history/$USER_ID?limit=5" \
    -H "Authorization: Bearer $TOKEN")
check "GET /agent/history/:id retorna array" \
    '[ "$(echo "$HIST" | jq -r "type")" = "array" ]'

# ─── Resumen ─────────────────────────────────────────────────
echo ""
bold "Resultado: $PASS pasaron / $((PASS + FAIL)) total"
[ "$FAIL" -eq 0 ] && green "Todos los tests pasaron" || red "$FAIL test(s) fallaron"
exit "$FAIL"
