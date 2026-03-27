#!/usr/bin/env bash
# Goal: To run the Preprocess Stage of the ML Pipeline
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PY="python"
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
fi

mkdir -p outputs/logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG="outputs/logs/preprocess_${TS}.log"

echo "[run_preprocess] Running preprocess stage..."

${PY} run/preprocess.py \
  --raw-root data/raw/H_glaber \
  --ingest-manifest data/raw/H_glaber_manifest.csv \
  --tiles-dir data/interim/tiles/H_glaber \
  --tiles-manifest data/interim/tiles/H_glaber_tiles_manifest.csv \
  --tile-size 512 \
  --min-tissue-ratio 0.05 \
  2>&1 | tee "${LOG}"

echo "[run_preprocess] Preprocess complete."