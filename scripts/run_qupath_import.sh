#!/usr/bin/env bash
# Purpose: Import images into a QuPath project from the data pipeline

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$REPO_ROOT/data/raw/H_glaber"
QUPATH_DIR="$REPO_ROOT/QuPath"
QUPATH_PROJECT_DIR="$QUPATH_DIR/project"
QUPATH_PROJECT_FILE="$QUPATH_PROJECT_DIR/nmr_ovarian_follicle.qpproj"
QUPATH_SCRIPTS_DIR="$QUPATH_DIR/scripts"
LOG_DIR="$REPO_ROOT/outputs/logs"

mkdir -p \
  "$QUPATH_PROJECT_DIR" \
  "$QUPATH_SCRIPTS_DIR" \
  "$LOG_DIR"

# QuPath path
QUPATH_BIN="${QUPATH_BIN:-$HOME/QuPath/bin/QuPath}"
IMPORT_SCRIPT="$QUPATH_SCRIPTS_DIR/import_images.groovy"

if [[ ! -x "$QUPATH_BIN" ]]; then
  echo "ERROR: QuPath executable not found or not executable:"
  echo "  $QUPATH_BIN"
  echo
  echo "Set it explicitly, for example:"
  echo '  export QUPATH_BIN="$HOME/QuPath/bin/QuPath"'
  exit 1
fi

if [[ ! -d "$RAW_DIR" ]]; then
  echo "ERROR: Raw image directory not found:"
  echo "  $RAW_DIR"
  exit 1
fi

if [[ ! -f "$IMPORT_SCRIPT" ]]; then
  echo "ERROR: Groovy import script not found:"
  echo "  $IMPORT_SCRIPT"
  exit 1
fi

echo "Using QuPath executable: $QUPATH_BIN"
echo "Project file: $QUPATH_PROJECT_FILE"
echo "Import script: $IMPORT_SCRIPT"
echo "Raw dir: $RAW_DIR"

"$QUPATH_BIN" script \
  --project "$QUPATH_PROJECT_FILE" \
  "$IMPORT_SCRIPT" \
  --args "$RAW_DIR"