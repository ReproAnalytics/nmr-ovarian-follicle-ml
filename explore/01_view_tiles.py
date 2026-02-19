#!/usr/bin/env python3
"""
explore/01_view_tiles.py

Purpose (EDA):
  Fast visual QC using the *_reduced.png images (no huge TIFF reads).
  - Samples N accessions from the raw manifest
  - Creates a montage grid of reduced images
  - Produces ML-relevant EDA outputs:
      * TIFF file size distribution
      * Reduced PNG resolution distribution (proxy for scan variability)
      * Reduced PNG brightness distribution (proxy for exposure / staining variability)
      * Metadata profile (counts, unique values, missingness) -> JSON
      * Cross-tab checks for confounding: life stage x stain_type -> CSV
      * Donor-level slide counts (imbalance / leakage risk) -> CSV

Inputs:
  - data/raw/H_glaber/manifest_raw.csv  (produced by explore/00_dataset_sanity.py)

Outputs (default):
  outputs/figures/
    - reduced_montage.png
    - file_sizes_mb.png

  outputs/reports/
    - metadata_profile.json
    - crosstab_lifestage_by_stain.csv
    - donor_slide_counts.csv

Run (from repo root):
  python explore/01_view_tiles.py
"""

from __future__ import annotations

import argparse
import math
import random
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Pillow for reading PNGs
from PIL import Image, ImageOps


# ------------------------------ utilities ------------------------------------

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
        img = ImageOps.exif_transpose(img)
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
) -> Image.Image:
    """
    Create a montage with simple labels (accession id).
    Uses fixed tile size = max width/height across selected images.
    """
    if not images:
        raise ValueError("No images to montage.")

    max_w = max(img.size[0] for _, img in images)
    max_h = max(img.size[1] for _, img in images)

    rows = int(math.ceil(len(images) / cols))

    tile_w = max_w
    tile_h = max_h + label_height
    canvas_w = cols * tile_w + (cols + 1) * tile_pad
    canvas_h = rows * tile_h + (rows + 1) * tile_pad

    canvas = Image.new("RGB", (canvas_w, canvas_h), (20, 20, 20))

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

        img_w, img_h = img.size
        x_img = x0 + (tile_w - img_w) // 2
        y_img = y0 + (max_h - img_h) // 2
        canvas.paste(img, (x_img, y_img))

        if draw is not None and font is not None:
            label_y = y0 + max_h + 2
            draw.text((x0 + 2, label_y), label, fill=(235, 235, 235), font=font)

    return canvas


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


def normalize_series(s: pd.Series) -> pd.Series:
    # Standardize strings: strip, empty->NaN
    s2 = s.copy()
    s2 = s2.astype("string")
    s2 = s2.str.strip()
    s2 = s2.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return s2


def metadata_profile(df: pd.DataFrame, cols: List[str], top_k: int = 10) -> Dict[str, object]:
    """
    Build a JSON-serializable profile for categorical metadata:
      - missing count
      - unique count
      - top values with counts (good replacement for bar charts)
    """
    prof: Dict[str, object] = {}
    n = len(df)

    for col in cols:
        if col not in df.columns:
            continue
        s = normalize_series(df[col])
        missing = int(s.isna().sum())
        present = int(n - missing)
        vc = s.dropna().astype(str).value_counts().head(top_k)

        prof[col] = {
            "n_rows": n,
            "present": present,
            "missing": missing,
            "n_unique": int(s.dropna().nunique()),
            "top_values": {k: int(v) for k, v in vc.items()},
        }

    return prof


# ------------------------------ main -----------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="EDA visual QC for reduced images + manifest summaries.")
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/raw/H_glaber/manifest_raw.csv")
    ap.add_argument("--figdir", default="outputs/figures")
    ap.add_argument("--reportdir", default="outputs/reports")
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-side", type=int, default=512)
    ap.add_argument("--only-ok", action="store_true")
    args = ap.parse_args()   

    root = repo_root()
    manifest_path = (root / args.manifest).resolve()
    figdir = (root / args.figdir).resolve()
    reportdir = (root / args.reportdir).resolve()
    ensure_dir(figdir)
    ensure_dir(reportdir)

    df = pd.read_csv(manifest_path)

    if args.only_ok and "ok" in df.columns:
        df = df[df["ok"] == True] 

    # Sample reduced PNGs
    candidates = []
    for _, r in df.iterrows():
        p = str(r.get("reduced_png_path", "")).strip()
        if not p:
            continue
        img_path = Path(p)
        if not img_path.is_absolute():
            img_path = (root / img_path).resolve()
        if img_path.exists():
            candidates.append((r, img_path))

    random.seed(args.seed)
    sample = candidates if len(candidates) <= args.n else random.sample(candidates, args.n)

    loaded: List[Tuple[str, Image.Image]] = []
    for r, img_path in sample:
        accession = str(r.get("accession_id", img_path.parent.name))
        img = safe_read_image(img_path, max_side=args.max_side)
        if img:
            loaded.append((accession, img))

    montage = make_montage(loaded, cols=max(1, args.cols))
    montage.save(figdir / "reduced_montage.png")

    # TIFF file size histogram
    if "tiff_size" in df.columns:
        mb = pd.to_numeric(df["tiff_size"], errors="coerce") / (1024 * 1024)
        plot_hist_numeric(
            mb,
            title="TIFF file size distribution (MB)",
            xlabel="Size (MB)",
            outpath=figdir / "file_sizes_mb.png",
        )

    # Metadata profile
    meta_cols = ["donorLifeStage", "stain_type", "magnification"]
    prof = metadata_profile(df, meta_cols)
    (reportdir / "metadata_profile.json").write_text(json.dumps(prof, indent=2))

    # Cross-tab
    if "donorLifeStage" in df.columns and "stain_type" in df.columns:
        a = normalize_series(df["donorLifeStage"])
        b = normalize_series(df["stain_type"])
        xtab = pd.crosstab(a.fillna("MISSING"), b.fillna("MISSING"))
        xtab.to_csv(reportdir / "crosstab_lifestage_by_stain.csv")

    # Donor slide counts
    if "donorID" in df.columns:
        d = normalize_series(df["donorID"])
        donor_counts = d.value_counts().rename_axis("donorID").reset_index(name="n_slides")
        donor_counts.to_csv(reportdir / "donor_slide_counts.csv", index=False)

# -------------------- console summary ------------------------------------

    print("\nEDA: View Tiles Summary")
    print("================================")
    print(f"Manifest used: {manifest_path}")
    print(f"Total rows in manifest: {len(df)}")
    print(f"Slides sampled for montage: {len(loaded)}")

    print("\nFigures written:")
    print(f"  - {figdir / 'reduced_montage.png'}")

    if "tiff_size" in df.columns:
        print(f"  - {figdir / 'file_sizes_mb.png'}")

    print("\nReports written:")
    print(f"  - {reportdir / 'metadata_profile.json'}")

    if "donorLifeStage" in df.columns and "stain_type" in df.columns:
        print(f"  - {reportdir / 'crosstab_lifestage_by_stain.csv'}")

    if "donorID" in df.columns:
        print(f"  - {reportdir / 'donor_slide_counts.csv'}")

    print("\nEDA completed successfully.\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())