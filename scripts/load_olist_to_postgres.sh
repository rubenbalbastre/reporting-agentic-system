#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${1:-data/raw/olist}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PG_SERVICE="${PG_SERVICE:-postgres}"
PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-reporting}"
TMP_DIR="/tmp/olist"

if [[ ! -d "$DATA_DIR" ]]; then
  echo "Dataset folder not found: $DATA_DIR"
  echo "Run: make kaggle-download"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found"
  exit 1
fi

echo "Ensuring postgres container is running..."
docker compose -f "$COMPOSE_FILE" up -d "$PG_SERVICE" >/dev/null

PG_CID="$(docker compose -f "$COMPOSE_FILE" ps -q "$PG_SERVICE")"
if [[ -z "$PG_CID" ]]; then
  echo "Could not resolve postgres container id"
  exit 1
fi

echo "Copying dataset files into container..."
docker exec "$PG_CID" sh -lc "rm -rf '$TMP_DIR' && mkdir -p '$TMP_DIR'"
docker cp "$DATA_DIR/." "$PG_CID:$TMP_DIR/"

echo "Applying schema..."
docker compose -f "$COMPOSE_FILE" exec -T "$PG_SERVICE" \
  psql -U "$PG_USER" -d "$PG_DB" -f /dev/stdin < infra/postgres/olist_schema.sql

load_csv() {
  local file="$1"
  local table="$2"

  if docker exec "$PG_CID" test -f "$TMP_DIR/$file"; then
    echo "Loading $file -> $table"
    docker compose -f "$COMPOSE_FILE" exec -T "$PG_SERVICE" psql -U "$PG_USER" -d "$PG_DB" -c \
      "\\copy $table FROM '$TMP_DIR/$file' CSV HEADER"
  else
    echo "Skipping missing file: $file"
  fi
}

load_csv "olist_customers_dataset.csv" "olist_customers"
load_csv "olist_geolocation_dataset.csv" "olist_geolocation"
load_csv "olist_order_items_dataset.csv" "olist_order_items"
load_csv "olist_order_payments_dataset.csv" "olist_order_payments"
load_csv "olist_order_reviews_dataset.csv" "olist_order_reviews"
load_csv "olist_orders_dataset.csv" "olist_orders"
load_csv "olist_products_dataset.csv" "olist_products"
load_csv "olist_sellers_dataset.csv" "olist_sellers"
load_csv "product_category_name_translation.csv" "olist_category_translation"

echo "Done. Quick check:"
docker compose -f "$COMPOSE_FILE" exec -T "$PG_SERVICE" psql -U "$PG_USER" -d "$PG_DB" -c \
  "SELECT 'olist_orders' AS table_name, COUNT(*) AS rows FROM olist_orders
   UNION ALL
   SELECT 'olist_order_items', COUNT(*) FROM olist_order_items
   UNION ALL
   SELECT 'olist_order_payments', COUNT(*) FROM olist_order_payments
   UNION ALL
   SELECT 'olist_customers', COUNT(*) FROM olist_customers;"
