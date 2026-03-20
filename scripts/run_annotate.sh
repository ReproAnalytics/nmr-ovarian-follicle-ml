#!/usr/bin/env bash
# Purpose: To facilitate the Annotate Stage and produce training-ready CSV.

set -euo pipefail

mkdir -p outputs/logs
TS="$(date +%Y%m%d_%H%M%S)"

CONFIG="${1:-configs/annotate.yaml}"

echo "[run_annotate] using config: ${CONFIG}"
python run/annotate.py --config "${CONFIG}" 2>&1 | tee "outputs/logs/annotate_${TS}.log"
