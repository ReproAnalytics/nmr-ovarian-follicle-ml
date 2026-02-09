#!/usr/bin/env bash
set -e

# Be sure to run script from your local home repo 'nmr-ovarian-follicle-ml'
PROJECT_ROOT="."

# -------------------------
# Environment
# -------------------------
mkdir -p "$PROJECT_ROOT/environment"
touch "$PROJECT_ROOT/environment/requirements.txt"

# -------------------------
# Configs
# -------------------------
mkdir -p "$PROJECT_ROOT/configs"
touch \
  "$PROJECT_ROOT/configs/dataset.yaml" \
  "$PROJECT_ROOT/configs/preprocess.yaml" \
  "$PROJECT_ROOT/configs/train.yaml" \
  "$PROJECT_ROOT/configs/infer.yaml" \
  "$PROJECT_ROOT/configs/eval.yaml"

# -------------------------
# Data (gitignored)
# -------------------------
mkdir -p \
  "$PROJECT_ROOT/data/raw" \
  "$PROJECT_ROOT/data/interim" \
  "$PROJECT_ROOT/data/processed"

# -------------------------
# Annotations
# -------------------------
mkdir -p "$PROJECT_ROOT/annotations/gold_set"
touch \
  "$PROJECT_ROOT/annotations/protocol.md" \
  "$PROJECT_ROOT/annotations/labelmap.json"

# -------------------------
# Outputs (gitignored)
# -------------------------
mkdir -p \
  "$PROJECT_ROOT/outputs/logs" \
  "$PROJECT_ROOT/outputs/models" \
  "$PROJECT_ROOT/outputs/predictions" \
  "$PROJECT_ROOT/outputs/metrics" \
  "$PROJECT_ROOT/outputs/figures" \
  "$PROJECT_ROOT/outputs/reports"

# -------------------------
# src (library code)
# -------------------------
mkdir -p \
  "$PROJECT_ROOT/src/ingest" \
  "$PROJECT_ROOT/src/preprocess" \
  "$PROJECT_ROOT/src/train" \
  "$PROJECT_ROOT/src/infer" \
  "$PROJECT_ROOT/src/postprocess" \
  "$PROJECT_ROOT/src/eval" \
  "$PROJECT_ROOT/src/utils"

touch \
  "$PROJECT_ROOT/src/ingest/ingest.py" \
  "$PROJECT_ROOT/src/preprocess/preprocess.py" \
  "$PROJECT_ROOT/src/train/train.py" \
  "$PROJECT_ROOT/src/infer/infer.py" \
  "$PROJECT_ROOT/src/postprocess/count.py" \
  "$PROJECT_ROOT/src/eval/evaluate.py" \
  "$PROJECT_ROOT/src/utils/config.py" \
  "$PROJECT_ROOT/src/utils/paths.py" \
  "$PROJECT_ROOT/src/utils/logging.py" \
  "$PROJECT_ROOT/src/utils/seed.py" \
  "$PROJECT_ROOT/src/utils/io.py"

# -------------------------
# run (execution interface)
# -------------------------
mkdir -p "$PROJECT_ROOT/run"
touch \
  "$PROJECT_ROOT/run/ingest.py" \
  "$PROJECT_ROOT/run/preprocess.py" \
  "$PROJECT_ROOT/run/train.py" \
  "$PROJECT_ROOT/run/infer.py" \
  "$PROJECT_ROOT/run/postprocess_count.py" \
  "$PROJECT_ROOT/run/eval_report.py"

# -------------------------
# explore
# -------------------------
mkdir -p "$PROJECT_ROOT/explore"
touch \
  "$PROJECT_ROOT/explore/00_dataset_sanity.py" \
  "$PROJECT_ROOT/explore/01_view_tiles.py" \
  "$PROJECT_ROOT/explore/02_overlay_masks.py" \
  "$PROJECT_ROOT/explore/03_annotation_audit.py" \
  "$PROJECT_ROOT/explore/04_error_analysis.py" \
  "$PROJECT_ROOT/explore/05_make_presentation_figs.py"

# -------------------------
# scripts (shell orchestration)
# -------------------------
mkdir -p "$PROJECT_ROOT/scripts"
touch \
  "$PROJECT_ROOT/scripts/env.sh" \
  "$PROJECT_ROOT/scripts/doctor.sh" \
  "$PROJECT_ROOT/scripts/run_stage.sh" \
  "$PROJECT_ROOT/scripts/setup_env.sh" \
  "$PROJECT_ROOT/scripts/run_ingest.sh" \
  "$PROJECT_ROOT/scripts/run_preprocess.sh" \
  "$PROJECT_ROOT/scripts/run_train.sh" \
  "$PROJECT_ROOT/scripts/run_infer.sh" \
  "$PROJECT_ROOT/scripts/run_postprocess_count.sh" \
  "$PROJECT_ROOT/scripts/run_eval_report.sh" \
  "$PROJECT_ROOT/scripts/run_pipeline.sh"

# -------------------------
# tests
# -------------------------
mkdir -p "$PROJECT_ROOT/tests"
touch "$PROJECT_ROOT/tests/test_config_loading.py"

echo "😊 Project scaffold created successfully."
