#!/usr/bin/env bash
set -e

PROJECT_ROOT="nmr-ovarian-follicle-ml"

echo "Creating project structure: $PROJECT_ROOT"

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

echo "✅ Martin scaffold created successfully."
