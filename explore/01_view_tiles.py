#!/usr/bin/env python3
"""
explore/01_view_tiles.py

Purpose (EDA):
  Fast visual QC using the *_reduced.png images (no huge TIFF reads).
  - Samples N accessions from the raw manifest
  - Creates a montage grid of reduced images
  - Generates a few quick, data-driven plots from the manifest (file sizes, life stage, stain, magnification, etc.)
  - Writes outputs to outputs/figures/

Inputs:
  - data/raw/H_glaber/manifest_raw.csv  (produced by explore/00_dataset_sanity.py)

Outputs (default):
  outputs/figures/
    - reduced_montage.png
    - file_sizes_mb.png
    - magnification_distribution.png
    - life_stage_counts.png
    - stain_type_counts.png

Run (from repo root):
  python explore/01_view_tiles.py
  python explore/01_view_tiles.py --n 25 --cols 5
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

# Pillow for reading PNGs
from PIL import Image, ImageOps


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def safe_read_image(path: Path, max_side: int = 512) -> Optional[Image.Image]:
    """
    Read an image safely and downscale so montage stays lightweight.
    Returns None if unreadable.
    """
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)  # handle any orientation tags
        img = img.convert("RGB")
        # downscale to max_side while preserving aspect ratio
        w, h = img.size
        scale = max(w, h) / float(max_side)
        if scale > 1.0:
            new_w = int(round(w / scale))
            new_h = int(round(h / scale))
            img = img.resize((new_w, new_h), resample=Image.BILINEAR)
        return img
    except Exception:
        return None


def make_montage(
    images: List[Tuple[str, Image.Image]],
    cols: int = 5,
    tile_pad: int = 8,
    label_height: int = 18,
    font_size: int = 10,
) -> Image.Image:
    """
    Create a montage with simple labels (accession id).
    Uses fixed tile size = max width/height across selected images.
    """
    if not images:
        raise ValueError("No images to montage.")

    # Determine tile size
    max_w = max(img.size[0] for _, img in images)
    max_h = max(img.size[1] for _, img in images)

    rows = int(math.ceil(len(images) / cols))

    # Canvas size
    tile_w = max_w
    tile_h = max_h + label_height
    canvas_w = cols * tile_w + (cols + 1) * tile_pad
    canvas_h = rows * tile_h + (rows + 1) * tile_pad

    canvas = Image.new("RGB", (canvas_w, canvas_h), (20, 20, 20))

    # Optional: use PIL's basic text (no external font dependency)
    try:
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
    except Exception:
        draw = None
        font = None

    for idx, (label, img) in enumerate(images):
        r = idx // cols
        c = idx % cols

        x0 = tile_pad + c * (tile_w + tile_pad)
        y0 = tile_pad + r * (tile_h + tile_pad)

        # center image within tile area (excluding label strip)
        img_w, img_h = img.size
        x_img = x0 + (tile_w - img_w) // 2
        y_img = y0 + (max_h - img_h) // 2
        canvas.paste(img, (x_img, y_img))

        # label strip
        if draw is not None and font is not None:
            label_y = y0 + max_h + 2
            draw.text((x0 + 2, label_y), label, fill=(235, 235, 235), font=font)

    return canvas


def plot_value_counts(
    s: pd.Series,
    title: str,
    outpath: Path,
    top_k: int = 12,
) -> None:
    s = s.dropna().astype(str).str.strip()
    s = s[s != ""]
    if s.empty:
        return

    vc = s.value_counts().head(top_k)
    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(111)
    ax.bar(vc.index.astype(str), vc.values)
    ax.set_title(title)
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def plot_hist_numeric(
    x: pd.Series,
    title: str,
    xlabel: str,
    outpath: Path,
    bins: int = 20,
) -> None:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if x.empty:
        return
    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(111)
    ax.hist(x.values, bins=bins)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)

def main() -> int:
    ap = argparse.ArgumentParser(description="EDA visual QC for reduced images + manifest summaries.")
    ap.add_argument(
        "--manifest",
        type=str,
        default="data/raw/H_glaber/manifest_raw.csv",
        help="Path to manifest_raw.csv (default: data/raw/H_glaber/manifest_raw.csv)",
    )
    ap.add_argument(
        "--outdir",
        type=str,
        default="outputs/figures",
        help="Directory to write figures (default: outputs/figures)",
    )
    ap.add_argument("--n", type=int, default=25, help="Number of accessions to sample for montage")
    ap.add_argument("--cols", type=int, default=5, help="Columns in montage grid")
    ap.add_argument("--seed", type=int, default=7, help="Random seed for sampling")
    ap.add_argument(
        "--max-side",
        type=int,
        default=512,
        help="Max side length for montage tiles (downscaled) (default: 512)",
    )
    ap.add_argument(
        "--only-ok",
        action="store_true",
        help="If set, only sample rows where ok==True",
    )
    args = ap.parse_args()

    root = repo_root()
    manifest_path = (root / args.manifest).resolve()
    outdir = (root / args.outdir).resolve()
    ensure_dir(outdir)

    if not manifest_path.exists():
        print(f"[ERROR] manifest not found: {manifest_path}")
        print("Run: python explore/00_dataset_sanity.py")
        return 2

    df = pd.read_csv(manifest_path)

    # Basic filtering
    if args.only_ok and "ok" in df.columns:
        df = df[df["ok"] == True]  # noqa: E712

    if df.empty:
        print("[ERROR] No rows available for montage after filtering.")
        return 2

    # Prefer reduced PNGs
    if "reduced_png_path" not in df.columns:
        print("[ERROR] manifest is missing 'reduced_png_path' column.")
        return 2

    # Sample rows that actually have an existing reduced PNG
    candidates = []
    for _, row in df.iterrows():
        p = str(row.get("reduced_png_path", "")).strip()
        if not p:
            continue
        img_path = Path(p)
        if not img_path.is_absolute():
            # Manifest likely stores absolute paths; but handle relative just in case
            img_path = (root / img_path).resolve()
        if img_path.exists():
            candidates.append((row, img_path))

    if not candidates:
        print("[ERROR] No existing reduced PNG files found from manifest.")
        return 2

    random.seed(args.seed)
    sample = candidates if len(candidates) <= args.n else random.sample(candidates, args.n)

    # Load images
    loaded: List[Tuple[str, Image.Image]] = []
    for row, img_path in sample:
        accession = str(row.get("accession_id", img_path.parent.name))
        img = safe_read_image(img_path, max_side=args.max_side)
        if img is None:
            continue
        loaded.append((accession, img))

    if not loaded:
        print("[ERROR] Failed to read any sampled reduced PNGs.")
        return 2

    # Montage
    montage = make_montage(loaded, cols=max(1, args.cols))
    montage_path = outdir / "reduced_montage.png"
    montage.save(montage_path)

    # --- Manifest-driven plots (quick EDA) -----------------------------------
    # File sizes in MB (TIFF is usually large-ish; still useful distribution)
    if "tiff_size" in df.columns:
        mb = pd.to_numeric(df["tiff_size"], errors="coerce") / (1024 * 1024)
        plot_hist_numeric(
            mb,
            title="TIFF file size distribution (MB)",
            xlabel="Size (MB)",
            outpath=outdir / "file_sizes_mb.png",
            bins=20,
        )

    # Magnification distribution (if present)
    if "magnification" in df.columns:
        # Extract numeric portion if values like "40x"
        mag = df["magnification"].astype(str).str.extract(r"(\d+\.?\d*)")[0]
        plot_hist_numeric(
            mag,
            title="Magnification distribution",
            xlabel="Magnification (x)",
            outpath=outdir / "magnification_distribution.png",
            bins=15,
        )

    # Life stage counts
    if "donorLifeStage" in df.columns:
        plot_value_counts(
            df["donorLifeStage"],
            title="Donor life stage counts",
            outpath=outdir / "life_stage_counts.png",
            top_k=15,
        )

    # Stain type counts
    if "stain_type" in df.columns:
        plot_value_counts(
            df["stain_type"],
            title="Stain type counts",
            outpath=outdir / "stain_type_counts.png",
            top_k=15,
        )

    # Sex counts
    if "donorSex" in df.columns:
        plot_value_counts(
            df["donorSex"],
            title="Donor sex counts",
            outpath=outdir / "sex_counts.png",
            top_k=10,
        )

    # Console summary
    print("\nEDA: View Tiles (reduced) Summary")
    print("================================")
    print(f"Manifest: {manifest_path}")
    print(f"Outdir:   {outdir}")
    print(f"Candidates with reduced PNG: {len(candidates)}")
    print(f"Montage images loaded:       {len(loaded)}")
    print("\nWrote:")
    print(f"  - {montage_path}")
    for p in sorted(outdir.glob("*.png")):
        if p.name != "reduced_montage.png":
            print(f"  - {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
