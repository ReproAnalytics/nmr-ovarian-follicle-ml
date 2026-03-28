#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PY="python"
if command -v python3 >/dev/null 2>&1; then PY="python3"; fi

mkdir -p outputs/logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG="outputs/logs/infer_${TS}.log"

${PY} run/infer.py "$@" 2>&1 | tee "${LOG}"
