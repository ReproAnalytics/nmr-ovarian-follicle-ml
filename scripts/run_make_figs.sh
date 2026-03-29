#!/usr/bin/env bash
# Goal: Generate results figures from CNN pipeline outputs
# Reads actual pipeline artifacts — no hardcoded values.

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
LOG="outputs/logs/make_figs_${TS}.log"

echo "[make_figs] Generating results figures..."

${PY} EDA/05_make_presentation_figs.py "$@" 2>&1 | tee "${LOG}"

echo "[make_figs] Complete. Figures: outputs/figures/results/"
