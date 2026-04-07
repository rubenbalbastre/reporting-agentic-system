#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${KAGGLE_USERNAME:-}" && -n "${KAGGLE_KEY:-}" ]]; then
  echo "Kaggle credentials found in environment (KAGGLE_USERNAME/KAGGLE_KEY)"
  exit 0
fi

if [[ ! -f "$HOME/.kaggle/kaggle.json" ]]; then
  echo "Kaggle credentials not found."
  echo "Option A: set KAGGLE_USERNAME and KAGGLE_KEY in your environment/.env"
  echo "Option B: place kaggle.json in $HOME/.kaggle/"
  exit 1
fi

chmod 600 "$HOME/.kaggle/kaggle.json"
echo "Kaggle credentials ready"
