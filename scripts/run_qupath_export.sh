#!/usr/bin/env bash
# Purpose: Export QuPath annotations and measurements back to the pipeline

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUPATH_DIR="$REPO_ROOT/QuPath"
QUPATH_PROJECT_DIR="$QUPATH_DIR/project"
QUPATH_SCRIPTS_DIR="$QUPATH_DIR/scripts"
ANNOTATIONS_DIR="$REPO_ROOT/annotations/raw_exports"
LOG_DIR="$REPO_ROOT/outputs/logs"
METRICS_DIR="$REPO_ROOT/outputs/metrics/qupath"

mkdir -p "$ANNOTATIONS_DIR" "$LOG_DIR" "$METRICS_DIR"

QUPATH_BIN="${QUPATH_BIN:-$HOME/opt/QuPath/bin/QuPath}"
EXPORT_SCRIPT="$QUPATH_SCRIPTS_DIR/export_annotations.groovy"

if [[ ! -x "$QUPATH_BIN" ]]; then
  echo "ERROR: QuPath executable not found or not executable:"
  echo "  $QUPATH_BIN"
  exit 1
fi

if [[ ! -f "$EXPORT_SCRIPT" ]]; then
  echo "ERROR: Groovy export script not found:"
  echo "  $EXPORT_SCRIPT"
  exit 1
fi

"$QUPATH_BIN" script \
  --project "$QUPATH_PROJECT_DIR" \
  "$EXPORT_SCRIPT" \
  "$ANNOTATIONS_DIR" \
  "$METRICS_DIR"
