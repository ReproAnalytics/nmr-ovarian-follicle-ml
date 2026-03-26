#!/usr/bin/env bash
# ============================================================
# run_qupath_import.sh
# Purpose: Import OME-TIFF images into a QuPath project
# ============================================================

set -euo pipefail

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$REPO_ROOT/data/raw/H_glaber"
QUPATH_DIR="$REPO_ROOT/QuPath"
QUPATH_PROJECT_DIR="$QUPATH_DIR/project"
QUPATH_PROJECT_FILE="$QUPATH_PROJECT_DIR/nmr_ovarian_follicle.qpproj"
QUPATH_SCRIPTS_DIR="$QUPATH_DIR/scripts"
LOG_DIR="$REPO_ROOT/outputs/logs"
LOG_FILE="$LOG_DIR/qupath_import_$(date +%Y%m%d_%H%M%S).log"

mkdir -p \
  "$QUPATH_PROJECT_DIR" \
  "$QUPATH_SCRIPTS_DIR" \
  "$LOG_DIR"

# ------------------------------------------------------------------
# QuPath binary (override with: export QUPATH_BIN=/path/to/QuPath)
# ------------------------------------------------------------------
QUPATH_BIN="${QUPATH_BIN:-$HOME/QuPath/bin/QuPath}"
IMPORT_SCRIPT="$QUPATH_SCRIPTS_DIR/import_images.groovy"

# ------------------------------------------------------------------
# Pre-flight checks
# ------------------------------------------------------------------
if [[ ! -x "$QUPATH_BIN" ]]; then
  echo "ERROR: QuPath executable not found or not executable:"
  echo "  $QUPATH_BIN"
  echo ""
  echo "Fix: export QUPATH_BIN=\"\$HOME/QuPath/bin/QuPath\""
  exit 1
fi

if [[ ! -d "$RAW_DIR" ]]; then
  echo "ERROR: Raw image directory not found:"
  echo "  $RAW_DIR"
  exit 1
fi

if [[ ! -f "$QUPATH_PROJECT_FILE" ]]; then
  echo "ERROR: QuPath project file not found:"
  echo "  $QUPATH_PROJECT_FILE"
  echo ""
  echo "Fix: open QuPath GUI → File → Project → Create project"
  echo "     Save it to: $QUPATH_PROJECT_DIR"
  exit 1
fi

if [[ ! -f "$IMPORT_SCRIPT" ]]; then
  echo "ERROR: Groovy import script not found:"
  echo "  $IMPORT_SCRIPT"
  exit 1
fi

# ------------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------------
echo "=================================================="
echo " QuPath Image Import"
echo "=================================================="
echo " Executable : $QUPATH_BIN"
echo " Project    : $QUPATH_PROJECT_FILE"
echo " Script     : $IMPORT_SCRIPT"
echo " Raw dir    : $RAW_DIR"
echo " Log        : $LOG_FILE"
echo "=================================================="

# ------------------------------------------------------------------
# Run  (--project MUST come before the script path)
# ------------------------------------------------------------------
"$QUPATH_BIN" script \
  --project "$QUPATH_PROJECT_FILE" \
  "$IMPORT_SCRIPT" \
  --args "$RAW_DIR" \
  2>&1 | tee "$LOG_FILE"

echo ""
echo "Done. Full log saved to: $LOG_FILE"