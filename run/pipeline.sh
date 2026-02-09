#!/usr/bin/env bash
# Goal: Script to run entire pipeline, from download, ingest to infer
# Author: Martin Orkuma

set -euo pipefail

# Resolve repo root as directory containing this script's parent
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3}"

echo "[pipeline] repo: $REPO_ROOT"
echo "[pipeline] python: $PYTHON"

# 1) Ingest (download + manifest)
$PYTHON run/ingest.py

# 2) Preprocess (stub example - implement later)
if [[ -f run/preprocess.py ]]; then
  $PYTHON run/preprocess.py
else
  echo "[pipeline] skipping preprocess (run/preprocess.py not found)"
fi

# 3) Train
if [[ -f run/train.py ]]; then
  $PYTHON run/train.py
else
  echo "[pipeline] skipping train (run/train.py not found)"
fi

# 4) Infer
if [[ -f run/infer.py ]]; then
  $PYTHON run/infer.py
else
  echo "[pipeline] skipping infer (run/infer.py not found)"
fi

# 5) Eval/report
if [[ -f run/eval_report.py ]]; then
  $PYTHON run/eval_report.py
else
  echo "[pipeline] skipping eval_report (run/eval_report.py not found)"
fi

echo "[pipeline] done."
