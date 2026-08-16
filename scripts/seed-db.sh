#!/usr/bin/env bash
# =============================================================
# Carga los datos de seed en la base de datos
# Uso: ./scripts/seed-db.sh
#
# Los datos de meses anteriores al actual son fijos (determinísticos).
# El mes en curso se puede parametrizar con estas variables de entorno:
#   ATTENDANCE_PCT=90       % de presentismo del mes actual (default 88)
#   LATE_COUNT_LAST_DAY=2   tardanzas forzadas en el último día hábil (default 0)
#
# Ej: ATTENDANCE_PCT=90 LATE_COUNT_LAST_DAY=2 ./scripts/seed-db.sh
#
# Requiere que el stack Docker esté corriendo
# =============================================================

set -euo pipefail

CONTAINER="${1:-kuaai-intelligent-hrms-postgres-1}"
DB="${POSTGRES_DB:-kuaai}"
USER="${POSTGRES_USER:-kuaai_user}"
ATTENDANCE_PCT="${ATTENDANCE_PCT:-88}"
LATE_COUNT_LAST_DAY="${LATE_COUNT_LAST_DAY:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILE="$SCRIPT_DIR/../infra/postgres/seed.sql"

echo "Cargando seed en contenedor $CONTAINER (attendance_pct=$ATTENDANCE_PCT, late_count_last_day=$LATE_COUNT_LAST_DAY)..."
docker exec -i "$CONTAINER" psql -U "$USER" -d "$DB" \
  -v attendance_pct="$ATTENDANCE_PCT" \
  -v late_count_last_day="$LATE_COUNT_LAST_DAY" \
  < "$SEED_FILE"
echo "Seed cargado correctamente."
