#!/usr/bin/env bash
# Goal: Verify the development environment is correctly set up.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PASS=0
FAIL=0

check() {
  if eval "$2" >/dev/null 2>&1; then
    echo "  😊 $1"
    ((PASS++))
  else
    echo "  ☠️ $1"
    ((FAIL++))
  fi
}

echo "Environment Doctor"
echo "=================="

check "Python 3.10+"            "python3 --version | grep -qE '3\.(1[0-9]|[2-9][0-9])'"
check ".venv exists"            "[ -d .venv ]"
check "pip available"           "python3 -m pip --version"
check "configs/ present"        "[ -f configs/dataset.yaml ]"
check "requirements.txt"        "[ -f environment/requirements.txt ]"
check "numpy importable"        "python3 -c 'import numpy'"
check "pandas importable"       "python3 -c 'import pandas'"
check "yaml importable"         "python3 -c 'import yaml'"
check "tifffile importable"     "python3 -c 'import tifffile'"
check "openslide importable"    "python3 -c 'import openslide'"

# Optional torch check (does not fail the doctor)
if python3 -c 'import torch' >/dev/null 2>&1; then
  echo "  😊 torch importable"
  ((PASS++))
else
  echo "  ⚠️  torch not installed (OK for now; required for deep learning training)"
  ((PASS++))
fi

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[ "${FAIL}" -eq 0 ] && echo "All checks passed!" || echo "Fix the above before continuing."
