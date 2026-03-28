#!/usr/bin/env python3
# Goal: Script to ingest histology and XML data from MOTHER db 
# Debugging and code assistance were provided by ChatGPT (GPT 5.2 Thinking) and Claude (Opus 4.6)

from __future__ import annotations
import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """
    Walk upward until we find a marker that indicates repo root.
    Adjust markers as needed.
    """
    markers = ["configs", "src", "environment", ".git", "README.md"]
    cur = start.resolve()
    for _ in range(20):
        if any((cur / m).exists() for m in markers):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError("Could not locate repo root. Run from inside the repo.")


def run_downloader(script_path: Path, dest_dir: Path) -> None:
    if not script_path.exists():
        raise FileNotFoundError(f"Downloader not found: {script_path}")
    if not os.access(script_path, os.X_OK):
        # Don't require chmod; just run via bash
        cmd = ["bash", str(script_path), str(dest_dir)]
    else:
        cmd = [str(script_path), str(dest_dir)]

    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"[ingest] Running downloader: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


# ---------- file-type classification (mirrors bash downloader logic) ----------
IMAGE_EXTS = {".tif", ".tiff"}
PREVIEW_EXTS = {".png"}
XML_EXTS = {".xml"}
 
MANIFEST_FIELDS = ["accession_id", "relpath", "filename", "extension", "file_type", "bytes"]
 
 
def classify_file_type(ext: str) -> str:
    """Derive file_type the same way the bash downloader does."""
    ext_lower = ext.lower()
    if ext_lower in IMAGE_EXTS:
        return "image"
    if ext_lower in XML_EXTS:
        return "xml"
    if ext_lower in PREVIEW_EXTS:
        return "preview"
    return "other"


def build_manifest(dest_dir: Path, manifest_path: Path) -> None:
    """
    Create a manifest of downloaded files: 
    accession_id, relpath, filename, extension, file_type, bytes
    """
    rows = []
    for acc_dir in sorted(p for p in dest_dir.iterdir() if p.is_dir()):
        accession = acc_dir.name
        for f in sorted(acc_dir.rglob("*")):
            if f.is_file():
                rows.append({
                    "accession_id": accession,
                    "relpath": str(f.relative_to(dest_dir)),
                    "filename": f.name,
                    "extension": ext,
                    "file_type": classify_file_type(ext),
                    "bytes": f.stat().st_size,
                })

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[ingest] Wrote manifest: {manifest_path} ({len(rows)} files)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest MOTHER NMR dataset into data/raw and build manifest.")
    parser.add_argument(
        "--dest",
        default="data/raw/H_glaber",
        help="Destination directory (repo-relative by default).",
    )
    parser.add_argument(
        "--manifest",
        default="data/raw/H_glaber_manifest.csv",
        help="Manifest path (repo-relative by default).",
    )
    parser.add_argument(
        "--downloader",
        default="scripts/download_mother_nmr.sh",
        help="Path to bash downloader (repo-relative by default).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step (only rebuild manifest).",
    )

    args = parser.parse_args()

    repo = find_repo_root(Path.cwd())
    dest_dir = (repo / args.dest).resolve()
    manifest_path = (repo / args.manifest).resolve()
    downloader = (repo / args.downloader).resolve()

    if not args.skip_download:
        run_downloader(downloader, dest_dir)
    else:
        print("[ingest] Skipping download (--skip-download)")
    
    # Build manifest
    build_manifest(dest_dir, manifest_path)
    
    print("="*30)
    print("INGEST COMPLETE")
    print("="*30)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
