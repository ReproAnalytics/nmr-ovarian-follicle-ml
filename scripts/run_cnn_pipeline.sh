#!/usr/bin/env bash
# Run the CNN training + evaluation pipeline
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
LOG="outputs/logs/cnn_pipeline_${TS}.log"

echo "[run_cnn_pipeline] Starting CNN pipeline..."
echo "[run_cnn_pipeline] Log: ${LOG}"

${PY} run/cnn_pipeline.py "$@" 2>&1 | tee "${LOG}"

echo "[run_cnn_pipeline] Complete."