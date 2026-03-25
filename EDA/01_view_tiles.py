#!/usr/bin/env python3
"""
explore/01_view_tiles.py

Purpose (EDA):
  Fast visual QC using the *_reduced.png images.
  - Samples N accessions from the raw manifest
  - Creates a montage grid of reduced images
  - Produces ML-relevant outputs:
      * TIFF file size distribution
      * Metadata profile JSON
      * Cross-tab: donorLifeStage x stain_type (CSV)
      * Donor slide counts (CSV)
      * Donor-level slide counts (CSV)

Inputs:
  - data/raw/H_glaber/manifest_raw.csv  (produced by explore/00_dataset_sanity.py)

Outputs:
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
    """Read an image safely and downscale so montage stays lightweight."""
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")

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
    """Create a montage with simple labels (accession id)."""
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
    s2 = s.astype("string").str.strip()
    s2 = s2.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return s2


def metadata_profile(df: pd.DataFrame, cols: List[str], top_k: int = 10) -> Dict[str, object]:
    """JSON profile for categorical metadata: missingness, unique count, top values."""
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


def find_reduced_png(accession_dir: Path) -> Optional[Path]:
    """
    Dynamically locate the reduced PNG inside an accession folder.

    Preference:
      1) exactly one *"_reduced.png"
      2) if multiple, choose shortest filename (usually canonical)
      3) if none, return None
    """
    hits = sorted(accession_dir.glob("*_reduced.png"))
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    return sorted(hits, key=lambda p: len(p.name))[0]


# ------------------------------ main -----------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="EDA visual QC for reduced images + manifest summaries.")
    ap.add_argument("--manifest", default="data/raw/H_glaber/manifest_raw.csv")
    ap.add_argument(
        "--raw-root",
        default="data/raw/H_glaber",
        help="Raw root containing accession folders (used to reconstruct *_reduced.png paths).",
    )
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
    raw_root = (root / args.raw_root).resolve()
    figdir = (root / args.figdir).resolve()
    reportdir = (root / args.reportdir).resolve()
    ensure_dir(figdir)
    ensure_dir(reportdir)

    if not manifest_path.exists():
        print(f"[ERROR] manifest not found: {manifest_path}")
        print("Run: python explore/00_dataset_sanity.py")
        return 2

    if not raw_root.exists():
        print(f"[ERROR] raw root not found: {raw_root}")
        return 2

    df = pd.read_csv(manifest_path)

    if args.only_ok and "ok" in df.columns:
        df = df[df["ok"] == True]  # noqa: E712

    if "accession_id" not in df.columns:
        print("[ERROR] manifest missing required column: accession_id")
        return 2

    if df.empty:
        print("[ERROR] No rows available after filtering.")
        return 2

    # Build candidate list by reconstructing reduced PNG paths from accession folders
    candidates: List[Tuple[pd.Series, Path]] = []
    missing_reduced = 0

    for _, r in df.iterrows():
        acc = str(r.get("accession_id", "")).strip()
        if not acc:
            continue

        acc_dir = raw_root / acc
        if not acc_dir.exists():
            continue

        reduced_png = find_reduced_png(acc_dir)
        if reduced_png is None or not reduced_png.exists():
            missing_reduced += 1
            continue

        candidates.append((r, reduced_png))

    if not candidates:
        print("[ERROR] No reduced PNGs found by reconstruction.")
        print(f"Checked raw root: {raw_root}")
        print("Expected pattern: data/raw/H_glaber/<accession_id>/*_reduced.png")
        return 2

    random.seed(args.seed)
    sample = candidates if len(candidates) <= args.n else random.sample(candidates, args.n)

    loaded: List[Tuple[str, Image.Image]] = []
    for r, img_path in sample:
        accession = str(r.get("accession_id", img_path.parent.name))
        img = safe_read_image(img_path, max_side=args.max_side)
        if img:
            loaded.append((accession, img))

    if not loaded:
        print("[ERROR] Failed to read any sampled reduced PNGs.")
        return 2

    montage = make_montage(loaded, cols=max(1, args.cols))
    montage_path = figdir / "reduced_montage.png"
    montage.save(montage_path)

    # TIFF file size histogram (if present)
    file_sizes_path: Optional[Path] = None
    if "tiff_size" in df.columns:
        mb = pd.to_numeric(df["tiff_size"], errors="coerce") / (1024 * 1024)
        file_sizes_path = figdir / "file_sizes_mb.png"
        plot_hist_numeric(
            mb,
            title="TIFF file size distribution (MB)",
            xlabel="Size (MB)",
            outpath=file_sizes_path,
        )

    # Reports
    meta_cols = ["donorLifeStage", "stain_type", "magnification"]
    prof = metadata_profile(df, meta_cols)
    metadata_profile_path = reportdir / "metadata_profile.json"
    metadata_profile_path.write_text(json.dumps(prof, indent=2), encoding="utf-8")

    crosstab_path: Optional[Path] = None
    if "donorLifeStage" in df.columns and "stain_type" in df.columns:
        a = normalize_series(df["donorLifeStage"])
        b = normalize_series(df["stain_type"])
        xtab = pd.crosstab(a.fillna("MISSING"), b.fillna("MISSING"))
        crosstab_path = reportdir / "crosstab_lifestage_by_stain.csv"
        xtab.to_csv(crosstab_path)

    donor_counts_path: Optional[Path] = None
    if "donorID" in df.columns:
        d = normalize_series(df["donorID"])
        donor_counts = d.value_counts().rename_axis("donorID").reset_index(name="n_slides")
        donor_counts_path = reportdir / "donor_slide_counts.csv"
        donor_counts.to_csv(donor_counts_path, index=False)

    # Console summary (explicit artifacts written)
    print("\nEDA: View Tiles Summary")
    print("================================")
    print(f"Manifest used: {manifest_path}")
    print(f"Raw root used: {raw_root}")
    print(f"Total rows in manifest: {len(df)}")
    print(f"Accessions with reduced PNG found: {len(candidates)}")
    print(f"Missing reduced PNG (among manifest rows checked): {missing_reduced}")
    print(f"Slides sampled for montage: {len(loaded)}")

    print("\nFigures written:")
    print(f"  - {montage_path}")
    if file_sizes_path is not None:
        print(f"  - {file_sizes_path}")

    print("\nReports written:")
    print(f"  - {metadata_profile_path}")
    if crosstab_path is not None:
        print(f"  - {crosstab_path}")
    if donor_counts_path is not None:
        print(f"  - {donor_counts_path}")

    print("\nEDA completed successfully.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())