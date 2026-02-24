#!/usr/bin/env bash
# Goal: One-time environment setup for nmr-ovarian-follicle-ml
# Author: Martin Orkuma
# Works on WSL (Ubuntu) + macOS

set -euo pipefail

# ---- Resolve repo root (script can be run from anywhere) ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

echo "=========================================="
echo "NMR Ovarian Follicle ML - Environment Setup"
echo "Repo: ${REPO_ROOT}"
echo "=========================================="

# ---- Choose python ----
PY="python"
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
fi

# ---- Check Python version ----
${PY} --version || { echo "ERROR: Python not found. Install Python 3.10+."; exit 1; }

# ---- Create venv (idempotent) ----
if [[ -d ".venv" ]]; then
  echo "Virtual environment already exists: .venv"
else
  echo "Creating virtual environment..."
  ${PY} -m venv .venv
fi

# ---- Activate ----
# shellcheck disable=SC1091
source .venv/bin/activate

# ---- Upgrade pip ----
echo "Upgrading pip..."
python -m pip install --upgrade pip
# If python=python3: 
# python3 -m pip install --upgrade pip

# ---- Install requirements ----
if [[ ! -f "environment/requirements.txt" ]]; then
  echo "ERROR: environment/requirements.txt not found."
  exit 1
fi

echo "Installing dependencies..."
pip install -r environment/requirements.txt

# ---- Create directories + .gitkeep ----
echo "Creating project directories..."
mkdir -p data/raw data/interim data/processed
mkdir -p outputs/logs outputs/models outputs/predictions outputs/metrics outputs/figures outputs/reports
mkdir -p annotations/gold_set

touch data/.gitkeep
touch outputs/logs/.gitkeep
touch outputs/models/.gitkeep
touch outputs/predictions/.gitkeep
touch outputs/metrics/.gitkeep
touch outputs/figures/.gitkeep
touch outputs/reports/.gitkeep
touch annotations/gold_set/.gitkeep

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1) Activate the environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2) Run ingest (downloads + writes manifest):"
echo "     python run/ingest.py"
echo ""
echo "  3) Run preprocess (tiles + tiles manifest):"
echo "     python run/preprocess.py"
echo ""
