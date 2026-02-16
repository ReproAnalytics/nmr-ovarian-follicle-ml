#!/bin/bash
# Goal: To run the Preprocess Stage of the ML Pipeline

set -e

echo "Running preprocess stage..."

python run/preprocess.py \
  --slide-manifest data/raw/H_glaber_manifest.csv \
  --raw-dir data/raw/H_glaber \
  --output-dir data/interim/tiles \
  --tile-manifest data/interim/tiles_manifest.csv \
  --tile-size 512 \
  --min-tissue-ratio 0.5 \
  2>&1 | tee outputs/logs/preprocess_$(date +%Y%m%d_%H%M%S).log

echo "Preprocess complete."