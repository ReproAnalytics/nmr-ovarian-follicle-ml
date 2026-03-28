#!/usr/bin/env bash
# Usage: bash scripts/run_stage.sh <stage_name> <entrypoint> [args...]
set -euo pipefail

STAGE="${1:?Usage: run_stage.sh <stage_name> <entrypoint> [args...]}"
ENTRYPOINT="${2:?}"
shift 2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"
source scripts/env.sh

mkdir -p outputs/logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG="outputs/logs/${STAGE}_${TS}.log"

echo "[${STAGE}] Starting at $(date)"
${PY} "${ENTRYPOINT}" "$@" 2>&1 | tee "${LOG}"
echo "[${STAGE}] Complete at $(date)"
