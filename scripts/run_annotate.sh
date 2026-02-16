#!/usr/bin/env bash
# Purpose: To run the annotate Stage
set -euo pipefail
mkdir -p outputs/logs
TS="$(date +%Y%m%d_%H%M%S)"
python run/annotate.py 2>&1 | tee "outputs/logs/annotate_${TS}.log"
