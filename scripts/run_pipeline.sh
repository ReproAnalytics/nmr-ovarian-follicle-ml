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

# 1) Ingest
bash scripts/run_ingest.sh

# 2) Preprocess (tile WSIs)
bash scripts/run_preprocess.sh

# 3) Annotate (validate QuPath exports → labeled_tiles.csv)
bash scripts/run_annotate.sh

# 4) Organize splits (labeled tiles → folder layout)
bash scripts/run_organize_splits.sh

# 4.5) (Optional) If tiles were exported via QuPath directly
bash scripts/sync_tiles.sh  

# 5) CNN Pipeline (train + eval + optional WSI inference)
bash scripts/run_cnn_pipeline.sh

# 6) Post-process (aggregate to slide-level counts)
bash scripts/run_postprocess_count.sh

echo "[pipeline] done."
