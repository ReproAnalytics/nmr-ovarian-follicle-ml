#!/bin/bash
# Goal: To run the Annotate (Validate Exports) Stage of the ML pipeline

set -euo pipefail

mkdir -p outputs/logs

TS="$(date +%Y%m%d_%H%M%S)"
LOG="outputs/logs/annotate_${TS}.log"

python run/validate_exports.py \
  --config configs/annotate.yaml \
  2>&1 | tee "${LOG}"
