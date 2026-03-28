#!/bin/bash
# Goal: To run the Post-process (Count) Stage of the ML pipeline

set -euo pipefail

mkdir -p outputs/logs

TS="$(date +%Y%m%d_%H%M%S)"
LOG="outputs/logs/postprocess_count_${TS}.log"

python run/postprocess_count.py \
  --predictions outputs/predictions/tiles_predictions.csv \
  --output outputs/predictions/slide_level_predictions.csv \
  2>&1 | tee "${LOG}"
