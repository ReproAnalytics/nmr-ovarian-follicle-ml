#!/bin/bash
# Goal: To run the Ingest Stage of the ML pipeline

set -e

echo "Running ingest stage..."
python run/ingest.py \
  --dest data/raw/H_glaber \
  --manifest data/raw/H_glaber_manifest.csv \
  2>&1 | tee outputs/logs/ingest_$(date +%Y%m%d_%H%M%S).log

echo "Ingest complete."