#!/usr/bin/env bash
# Goal: To run the Train stage of the ML pipeline.
# Usage examples:
#   bash scripts/run_train.sh
#   bash scripts/run_train.sh --dataset H_glaber

#   Note: Debugging and code assistance for the model training were provided by ChatGPT (GPT 5.2 Thinking)
set -euo pipefail

# -----------------------------
# Resolve repo root regardless of where script is run from
# -----------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# -----------------------------
# Defaults (edit if you standardize on H-glaber)
# -----------------------------
DATASET="H_glaber"   
SEED=42
TRAIN_RATIO="0.70"
VAL_RATIO="0.15"
TEST_RATIO="0.15"

TILES_MANIFEST="data/interim/tiles/${DATASET}_tiles_manifest.csv"
SPLITS_OUTDIR="data/processed"
MODELS_OUTDIR="outputs/models"
LABEL_COLUMN="label"
REQUIRE_LABELS="false"

# -----------------------------
# Simple argument parsing
# -----------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset)
      DATASET="$2"
      shift 2
      ;;
    --tiles-manifest)
      TILES_MANIFEST="$2"
      shift 2
      ;;
    --splits-outdir)
      SPLITS_OUTDIR="$2"
      shift 2
      ;;
    --models-outdir)
      MODELS_OUTDIR="$2"
      shift 2
      ;;
    --seed)
      SEED="$2"
      shift 2
      ;;
    --train-ratio)
      TRAIN_RATIO="$2"
      shift 2
      ;;
    --val-ratio)
      VAL_RATIO="$2"
      shift 2
      ;;
    --test-ratio)
      TEST_RATIO="$2"
      shift 2
      ;;
    --label-column)
      LABEL_COLUMN="$2"
      shift 2
      ;;
    --require-labels)
      REQUIRE_LABELS="true"
      shift 1
      ;;
    -h|--help)
      cat <<EOF
scripts/run_train.sh

Runs: python run/train.py with manifest-driven arguments.

Options:
  --dataset <name>              Dataset/species identifier used in default paths (default: H_glaber)
  --tiles-manifest <path>       Tiles manifest CSV path (default: data/interim/tiles/<DATASET>_tiles_manifest.csv)
  --splits-outdir <path>        Output dir for train/val/test split manifests (default: data/processed)
  --models-outdir <path>        Output dir for model artifacts (default: outputs/models)
  --seed <int>                  Split seed (default: 42)
  --train-ratio <float>         Train fraction (default: 0.70)
  --val-ratio <float>           Val fraction (default: 0.15)
  --test-ratio <float>          Test fraction (default: 0.15)
  --label-column <name>         Label column name (default: label)
  --require-labels              Fail if label column missing/empty
EOF
      exit 0
      ;;
    *)
      echo "[run_train] ERROR: Unknown argument: $1" >&2
      echo "[run_train] Run: bash scripts/run_train.sh --help" >&2
      exit 2
      ;;
  esac
done

# Recompute defaults if dataset changed and user did not override tiles manifest explicitly
# (Only adjust if the manifest path is still using the original pattern.)
DEFAULT_PATTERN="data/interim/tiles/${DATASET}_tiles_manifest.csv"
if [[ "${TILES_MANIFEST}" == "data/interim/tiles/H_glaber_tiles_manifest.csv" || "${TILES_MANIFEST}" == "data/interim/tiles/H-glaber_tiles_manifest.csv" ]]; then
  TILES_MANIFEST="${DEFAULT_PATTERN}"
fi

# -----------------------------
# Pick python launcher
# -----------------------------
PY="python"
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
fi

# -----------------------------
# Logging
# -----------------------------
mkdir -p outputs/logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG="outputs/logs/train_${DATASET}_${TS}.log"

echo "[run_train] Repo root: ${REPO_ROOT}"
echo "[run_train] Dataset: ${DATASET}"
echo "[run_train] Tiles manifest: ${TILES_MANIFEST}"
echo "[run_train] Splits outdir: ${SPLITS_OUTDIR}"
echo "[run_train] Models outdir: ${MODELS_OUTDIR}"
echo "[run_train] Ratios: train=${TRAIN_RATIO} val=${VAL_RATIO} test=${TEST_RATIO}"
echo "[run_train] Seed: ${SEED}"
echo "[run_train] Logging to: ${LOG}"
echo

# -----------------------------
# Run
# -----------------------------
CMD=(
  "${PY}" "run/train.py"
  "--tiles-manifest" "${TILES_MANIFEST}"
  "--splits-outdir" "${SPLITS_OUTDIR}"
  "--models-outdir" "${MODELS_OUTDIR}"
  "--seed" "${SEED}"
  "--train-ratio" "${TRAIN_RATIO}"
  "--val-ratio" "${VAL_RATIO}"
  "--test-ratio" "${TEST_RATIO}"
  "--label-column" "${LABEL_COLUMN}"
)

if [[ "${REQUIRE_LABELS}" == "true" ]]; then
  CMD+=("--require-labels")
fi

# Stream + save logs
"${CMD[@]}" 2>&1 | tee "${LOG}"

echo
echo "[run_train] Train stage complete."
