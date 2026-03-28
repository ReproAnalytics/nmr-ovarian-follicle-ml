#!/usr/bin/env bash
# scripts/run_train.sh — Activate existing venv and launch the CNN pipeline
# Run from repo root:  bash scripts/run_train.sh [--skip-wsi]
set -euo pipefail

# ── Resolve repo root from script location ──
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
echo ">>> Repo root: ${REPO_ROOT}"

VENV_DIR="${REPO_ROOT}/.venv"

# ── 1. System dependency (OpenSlide C library) ──
if ! dpkg -s openslide-tools &>/dev/null; then
    echo ">>> Installing system-level OpenSlide library..."
    sudo apt-get update -qq && sudo apt-get install -y openslide-tools
fi

# ── 2. Activate existing venv ──
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: .venv not found at ${VENV_DIR}"
    echo "       Create it first:  python3 -m venv .venv"
    exit 1
fi

source "${VENV_DIR}/bin/activate"
echo ">>> Using Python: $(which python)  ($(python --version))"

# ── 3. Install / update Python dependencies ──
echo ">>> Syncing Python packages..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ── 4. Run the pipeline ──
echo ""
echo ">>> Launching CNN pipeline..."
python run/cnn_script.py \
    --config configs/train.yaml \
    "$@"
