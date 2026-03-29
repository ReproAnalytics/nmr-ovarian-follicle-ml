#!/usr/bin/env bash
# Goal: Sync QuPath-exported tile images from CNN/ to data/processed/H_glaber/
# This script copies them to data/processed/H_glaber/ for cnn_pipeline.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

SRC="CNN"
DEST="data/processed/H_glaber"

if [[ ! -d "$SRC" ]]; then
  echo "ERROR: Source directory not found: $SRC"
  echo "Ask teammates to export QuPath tiles into CNN/{train,valid,test}/<class>/"
  exit 1
fi

echo "[sync_tiles] Syncing ${SRC}/ → ${DEST}/"

mkdir -p "$DEST"

# rsync mirrors the folder structure; --delete keeps dest in sync with source
rsync -av --delete "${SRC}/" "${DEST}/"

echo ""
echo "[sync_tiles] Summary:"
for split in train valid test; do
  if [[ -d "${DEST}/${split}" ]]; then
    n_classes=$(find "${DEST}/${split}" -mindepth 1 -maxdepth 1 -type d | wc -l)
    n_tiles=$(find "${DEST}/${split}" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.tif" \) | wc -l)
    echo "  ${split}: ${n_tiles} tiles across ${n_classes} classes"
  else
    echo "  ${split}: not found"
  fi
done

echo ""
echo "[sync_tiles] Done. Ready to run: bash scripts/run_cnn_pipeline.sh"