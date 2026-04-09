#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-reporting}"
BACKEND_SERVICE="${BACKEND_SERVICE:-backend}"
SHARED_JOBS_DIR="${SHARED_JOBS_DIR:-/data/shared/jobs}"

SQL="TRUNCATE TABLE messages, conversations, reports RESTART IDENTITY CASCADE;"

docker compose exec -T "$POSTGRES_SERVICE" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$SQL"

docker compose exec -T "$BACKEND_SERVICE" sh -lc \
  "mkdir -p '$SHARED_JOBS_DIR' && find '$SHARED_JOBS_DIR' -mindepth 1 -maxdepth 1 -type d -name 'report_*' -exec rm -rf {} +"

echo "Done. Truncated tables: messages, conversations, reports"
echo "Done. Removed shared volume report folders under: $SHARED_JOBS_DIR/report_*"
