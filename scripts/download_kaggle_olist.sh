#!/usr/bin/env bash
set -euo pipefail

DATASET="${KAGGLE_DATASET:-olistbr/brazilian-ecommerce}"
OUT_DIR="${1:-data/raw/olist}"

if ! command -v kaggle >/dev/null 2>&1; then
  echo "kaggle CLI not found locally. Using Docker fallback..."

  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found and kaggle CLI not installed locally."
    echo "Install one of:"
    echo " - pip install kaggle"
    echo " - docker"
    exit 1
  fi

  if [[ -z "${KAGGLE_USERNAME:-}" || -z "${KAGGLE_KEY:-}" ]]; then
    echo "KAGGLE_USERNAME/KAGGLE_KEY must be set for Docker fallback."
    exit 1
  fi

  mkdir -p "$OUT_DIR"

  docker run --rm \
    -e KAGGLE_USERNAME="$KAGGLE_USERNAME" \
    -e KAGGLE_KEY="$KAGGLE_KEY" \
    -v "$(pwd)/$OUT_DIR:/work" \
    python:3.11-slim \
    sh -lc "pip install --no-cache-dir kaggle >/dev/null && kaggle datasets download -d '$DATASET' -p /work --unzip"

  echo "Download complete (Docker): $OUT_DIR"
  ls -1 "$OUT_DIR" | sed 's/^/ - /'
  exit 0
fi

mkdir -p "$OUT_DIR"

echo "Downloading dataset: $DATASET"
kaggle datasets download -d "$DATASET" -p "$OUT_DIR" --unzip

echo "Download complete: $OUT_DIR"
ls -1 "$OUT_DIR" | sed 's/^/ - /'
