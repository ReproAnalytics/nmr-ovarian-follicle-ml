#!/bin/bash
# Goal: To run the Organize Splits Stage of the ML pipeline

set -euo pipefail

mkdir -p outputs/logs

TS="$(date +%Y%m%d_%H%M%S)"
LOG="outputs/logs/organize_splits_${TS}.log"

python run/organize_splits.py \
  --gold-csv annotations/gold_set/labeled_tiles.csv \
  --output data/processed/H_glaber \
  --train-ratio 0.7 \
  --valid-ratio 0.15 \
  --seed 42 \
  2>&1 | tee "${LOG}"