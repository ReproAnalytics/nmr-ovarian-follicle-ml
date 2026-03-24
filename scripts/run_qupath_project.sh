#!/usr/bin/env bash
# Purpose: Script to Run QuPath from the Data Pipeline

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$REPO_ROOT/data/raw/H_glaber"
QUPATH_DIR="$REPO_ROOT/QuPath"
QUPATH_PROJECT_DIR="$QUPATH_DIR/project"
QUPATH_SCRIPTS_DIR="$QUPATH_DIR/scripts"
ANNOTATIONS_DIR="$REPO_ROOT/annotations/raw_exports"
LOG_DIR="$REPO_ROOT/outputs/logs"


mkdir -p \
"$QUPATH_PROJECT_DIR" \
"$QUPATH_SCRIPTS_DIR" \
"$ANNOTATIONS_DIR" \
"$LOG_DIR"

# QuPath path
QUPATH_BIN="${QUPATH_BIN:-$HOME/opt/QuPath/bin/QuPath}"

IMPORT_SCRIPT="$QUPATH_SCRIPTS_DIR/import_images.groovy"

if [[ ! -x "$QUPATH_BIN" ]]; then
  echo "ERROR: QuPath executable not found or not executable:"
  echo "  $QUPATH_BIN"
  echo
  echo "Expected example:"
  echo "  $HOME/opt/QuPath/bin/QuPath"
  exit 1
fi

if [[ ! -f "$IMPORT_SCRIPT" ]]; then
  echo "ERROR: Groovy import script not found:"
  echo "  $IMPORT_SCRIPT"
  exit 1
fi

echo "Using QuPath executable: $QUPATH_BIN"
echo "Project dir: $QUPATH_PROJECT_DIR"
echo "Import script: $IMPORT_SCRIPT"
echo "Raw dir: $RAW_DIR"
echo "Annotations dir: $ANNOTATIONS_DIR"

"$QUPATH_BIN" script \
  --project "$QUPATH_PROJECT_DIR" \
  "$IMPORT_SCRIPT" \
  "$RAW_DIR" \
  "$ANNOTATIONS_DIR"
