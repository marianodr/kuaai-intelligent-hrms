#!/usr/bin/env bash
# =============================================================
# Carga los datos de seed en la base de datos
# Uso: ./scripts/seed-db.sh
# Requiere que el stack Docker esté corriendo
# =============================================================

set -euo pipefail

CONTAINER="${1:-kuaai-intelligent-hrms-postgres-1}"
DB="${POSTGRES_DB:-kuaai}"
USER="${POSTGRES_USER:-kuaai_user}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILE="$SCRIPT_DIR/../infra/postgres/seed.sql"

echo "Cargando seed en contenedor $CONTAINER..."
docker exec -i "$CONTAINER" psql -U "$USER" -d "$DB" < "$SEED_FILE"
echo "Seed cargado correctamente."
