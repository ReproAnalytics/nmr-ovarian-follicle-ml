#!/usr/bin/env bash
# scripts/env.sh — Source this from other scripts for shared defaults.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Activate venv if present
if [[ -f "${REPO_ROOT}/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.venv/bin/activate"
fi

# Pick python
export PY="python"
if command -v python3 >/dev/null 2>&1; then
  export PY="python3"
fi

cd "${REPO_ROOT}"