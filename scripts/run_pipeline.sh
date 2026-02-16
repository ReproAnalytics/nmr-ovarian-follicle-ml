#!/usr/bin/env bash
# ------------------------------------------------------------------------------------
# Purpose: End-to-end pipeline orchestration. 
# Authors: Julian Coles, Martin Orkuma, Pamela Styborski, and Silvia Tenempaguay-Nunez
# ------------------------------------------------------------------------------------

set -euo pipefail

# Resolve repo root as the directory containing this script's parent
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3}"

echo "[pipeline] repo: $REPO_ROOT"
echo "[pipeline] python: $PYTHON"

# 1) Ingest (download + manifest)
bash scripts/run_ingest.sh

# 2) Preprocess (stub example - implement later)
bash scripts/run_preprocess.sh

# 3) Train
bash scripts/run_train.sh

# 4) Infer
# bash scripts/run_infer.sh

# 5) Post-process
# bash scripts/run_postprocess_count.sh

# 6) Eval/report
# bash scripts/run_eval_report.sh

echo "[pipeline] done."
