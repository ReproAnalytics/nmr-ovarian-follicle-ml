#!/usr/bin/env python3
"""
Preprocess stage entry point aligned with run/ingest.py (filesystem-derived CSV manifest).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# -----------------------------
# Helpers
# -----------------------------

@dataclass
class SlideRecord:
    accession_id: str
    relpath: str
    filename: str
    bytes: int

    @property
    def suffix(self) -> str:
        return Path(self.filename).suffix.lower()


def read_ingest_manifest(manifest_csv: Path) -> List[SlideRecord]:
    if not manifest_csv.exists():
        raise FileNotFoundError(f"Ingest manifest not found: {manifest_csv}")

    records: List[SlideRecord] = []
    with manifest_csv.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        required = {"accession_id", "relpath", "filename", "bytes"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(
                f"Manifest missing required columns. Expected {sorted(required)} "
                f"but got {sorted(reader.fieldnames or [])}"
            )

        for row in reader:
            records.append(
                SlideRecord(
                    accession_id=row["accession_id"],
                    relpath=row["relpath"],
                    filename=row["filename"],
                    bytes=int(row["bytes"]) if row["bytes"] else 0,
                )
            )
    return records


def filter_slide_files(
    records: Iterable[SlideRecord],
    allowed_exts: Tuple[str, ...],
) -> List[SlideRecord]:
    allowed_exts = tuple(e.lower() for e in allowed_exts)
    slides = [r for r in records if r.filename.lower().endswith(allowed_exts)]
    return slides


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# -----------------------------
# Tiling stub / integration point
# -----------------------------
def generate_tiles_for_slide(
    slide_path: Path,
    out_dir: Path,
    tile_size: int,
    stride: Optional[int],
    level: int,
    min_tissue_ratio: float,
    normalize: str,
) -> List[Dict[str, object]]:
    """
    Integration point:
    - Replace this stub with your real tiling implementation (e.g., openslide/ome-tiff reader).
    - For now, it only records "planned" tile settings for each slide.

    Returns:
        List of tile entries (one per tile) OR (for stub) one record per slide.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- STUB BEHAVIOR ----
    # We output a single entry per slide, so the rest of the pipeline wiring works.
    # When you implement real tiling, emit one row per tile with tile filepaths.
    return [{
        "slide_path": str(slide_path),
        "tile_path": "",  # fill when actual tiles are written
        "tile_size": tile_size,
        "stride": stride if stride is not None else "",
        "level": level,
        "min_tissue_ratio": min_tissue_ratio,
        "normalize": normalize,
        "status": "stub_no_tiles_written",
    }]


def write_tiles_manifest(rows: List[Dict[str, object]], out_csv: Path) -> None:
    ensure_parent(out_csv)
    if not rows:
        # Still write headers if no rows, so downstream stages have a file to read.
        headers = [
            "slide_path", "tile_path", "tile_size", "stride", "level",
            "min_tissue_ratio", "normalize", "status"
        ]
        with out_csv.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=headers)
            writer.writeheader()
        return

    headers = list(rows[0].keys())
    with out_csv.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


# -----------------------------
# Main
# -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preprocess (tiling) stage aligned with ingest.py manifest."
    )
    parser.add_argument(
        "--raw-root",
        default="data/raw/H_glaber",
        help="Root directory that contains accession subfolders downloaded by ingest.",
    )
    parser.add_argument(
        "--ingest-manifest",
        default="data/raw/H_glaber_manifest.csv",
        help="CSV manifest produced by run/ingest.py.",
    )
    parser.add_argument(
        "--tiles-dir",
        default="data/interim/tiles/H_glaber",
        help="Directory where tiles will be written.",
    )
    parser.add_argument(
        "--tiles-manifest",
        default="data/interim/tiles/H_glaber_tiles_manifest.csv",
        help="Output CSV manifest listing tiles.",
    )

    # Tiling params (mirrors what you were previously building from YAML)
    parser.add_argument("--tile-size", type=int, default=512, help="Tile width/height in pixels.")
    parser.add_argument("--stride", type=int, default=512, help="Stride in pixels (default=tile-size).")
    parser.add_argument("--level", type=int, default=0, help="Pyramid level to read from (0 = highest resolution).")
    parser.add_argument("--min-tissue-ratio", type=float, default=0.05, help="Skip tiles with tissue ratio below this.")
    parser.add_argument("--normalize", default="none", help="Normalization method label (e.g., none, macenko, reinhard).")

    # Slide file types
    parser.add_argument(
        "--slide-exts",
        default=".ome.tif,.ome.tiff,.tif,.tiff",
        help="Comma-separated slide extensions to include.",
    )

    # Logging
    parser.add_argument(
        "--log",
        default="outputs/logs/preprocess_" + now_stamp() + ".log",
        help="Log file path.",
    )

    args = parser.parse_args()

    # Prep paths
    raw_root = Path(args.raw_root)
    ingest_manifest = Path(args.ingest_manifest)
    tiles_dir = Path(args.tiles_dir)
    tiles_manifest = Path(args.tiles_manifest)
    log_path = Path(args.log)

    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        line = f"[preprocess] {msg}"
        print(line)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")

    log("=" * 60)
    log("PREPROCESS STAGE")
    log(f"raw_root: {raw_root}")
    log(f"ingest_manifest: {ingest_manifest}")
    log(f"tiles_dir: {tiles_dir}")
    log(f"tiles_manifest: {tiles_manifest}")

    # Read manifest from ingest
    records = read_ingest_manifest(ingest_manifest)

    allowed_exts = tuple(e.strip().lower() for e in args.slide_exts.split(",") if e.strip())
    slide_records = filter_slide_files(records, allowed_exts=allowed_exts)

    log(f"Manifest rows: {len(records)}")
    log(f"Slide files matched ({allowed_exts}): {len(slide_records)}")

    # Build tiles
    all_tile_rows: List[Dict[str, object]] = []

    stride = args.stride if args.stride else args.tile_size
    if stride <= 0:
        stride = args.tile_size

    for r in slide_records:
        slide_path = (raw_root / r.relpath).resolve()
        if not slide_path.exists():
            log(f"WARNING: missing slide file on disk: {slide_path}")
            continue

        # Organize outputs by accession_id to keep things tidy
        slide_out_dir = tiles_dir / r.accession_id

        tile_rows = generate_tiles_for_slide(
            slide_path=slide_path,
            out_dir=slide_out_dir,
            tile_size=args.tile_size,
            stride=stride,
            level=args.level,
            min_tissue_ratio=args.min_tissue_ratio,
            normalize=args.normalize,
        )

        all_tile_rows.extend(tile_rows)

    write_tiles_manifest(all_tile_rows, tiles_manifest)

    log(f"Wrote tiles manifest: {tiles_manifest} (rows={len(all_tile_rows)})")
    log("PREPROCESS STAGE COMPLETE")
    log("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
