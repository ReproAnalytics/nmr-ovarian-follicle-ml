#!/bin/bash
# Goal: To run the Ingest Stage of the ML pipeline

set -euo pipefail

mkdir -p outputs/logs

TS="$(date +%Y%m%d_%H%M%S)"
LOG="outputs/logs/ingest_${TS}.log"

# If you want to skip downloads by default, set SKIP_DOWNLOAD=1
SKIP_FLAG=""
if [[ "${SKIP_DOWNLOAD:-0}" == "1" ]]; then
  SKIP_FLAG="--skip-download"
fi

python run/ingest.py \
  --dest data/raw/H_glaber \
  --manifest data/raw/H_glaber_manifest.csv \
  ${SKIP_FLAG} \
  2>&1 | tee "${LOG}"