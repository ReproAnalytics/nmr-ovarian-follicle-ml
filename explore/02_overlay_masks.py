#!/usr/bin/env python3
"""
explore/02_overlay_masks.py

Purpose (EDA):
  Overlay annotation shapes (polygons/ROIs) onto the *_reduced.png previews for fast QA.

Designed for QuPath-style exports (most common):
  - GeoJSON FeatureCollection with Polygon/MultiPolygon geometries
  - Each Feature may have a class name under one of:
      properties.class
      properties.name
      properties.classification.name
      properties.objectType / properties.type  (fallback)

Inputs:
  - data/raw/H_glaber/manifest_raw.csv          (from explore/00_dataset_sanity.py)
  - annotations/raw_exports/                   (directory containing per-slide annotation files)
  - (optional) annotations/labelmap.json       (used to standardize class names; not required)

Outputs:
  - outputs/figures/overlays/<accession>_overlay.png
  - outputs/reports/overlay_audit.csv           (what was found/used, per accession)

Key idea:
  Annotations are usually in FULL-RES slide coordinates, while *_reduced.png is downscaled.
  We compute a scale factor:
      sx = reduced_width / full_width
      sy = reduced_height / full_height

Full-res dimensions are obtained by:
  1) Reading the TIFF header via tifffile (if installed), else
  2) You provide --full-width/--full-height (applies to all), else
  3) We skip overlay and record "missing_full_dims".

Run (from repo root):
  python explore/02_overlay_masks.py
  python explore/02_overlay_masks.py --n 15 --seed 7
  python explore/02_overlay_masks.py --ann-dir annotations/raw_exports --pattern "{accession}*.geojson"
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from PIL import Image, ImageDraw, ImageOps

# Optional TIFF introspection
try:
    import tifffile  # type: ignore
except Exception:
    tifffile = None


# -----------------------------
# Helpers
# -----------------------------

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def normalize_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def deterministic_color(label: str) -> Tuple[int, int, int]:
    """
    Deterministic RGB color from a label string (no external deps).
    """
    h = 0
    for ch in label.encode("utf-8"):
        h = (h * 131 + ch) % 2_147_483_647
    # Spread into RGB (avoid too-dark colors)
    r = 60 + (h % 160)
    g = 60 + ((h // 7) % 160)
    b = 60 + ((h // 13) % 160)
    return int(r), int(g), int(b)


def safe_read_image(path: Path) -> Optional[Image.Image]:
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        return img.convert("RGBA")
    except Exception:
        return None


def get_full_dims_from_tiff(tiff_path: Path) -> Optional[Tuple[int, int]]:
    """
    Try to extract full-res (width, height) from TIFF header without loading pixels.
    Works for many OME-TIFFs and regular TIFFs.
    """
    if tifffile is None:
        return None
    try:
        with tifffile.TiffFile(str(tiff_path)) as tf:
            # Prefer first series shape
            if tf.series:
                shape = getattr(tf.series[0], "shape", None)
                if shape is None:
                    return None
                # shape can be (Y, X), (Y, X, C), (Z, Y, X, C), etc.
                # Take last two spatial dims as (Y, X) if available.
                if len(shape) >= 2:
                    h = int(shape[-2])
                    w = int(shape[-1])
                    # If channel last, shape[-1] may be C not X; handle common cases:
                    # If last dim is small (<=4) and previous is large, assume last is C.
                    if w <= 4 and len(shape) >= 3:
                        w = int(shape[-2])
                        h = int(shape[-3])
                    return (w, h)
            # Fallback: use first page
            page0 = tf.pages[0]
            return (int(page0.imagewidth), int(page0.imagelength))
    except Exception:
        return None


def find_annotation_file(ann_dir: Path, pattern: str, accession: str, slide_id: Optional[str]) -> Optional[Path]:
    """
    Find an annotation file using a simple glob pattern.
    Pattern may include:
      {accession}  e.g. MDB0000530
      {slideID}    optional, from XML manifest
    """
    candidates: List[Path] = []

    pat = pattern.replace("{accession}", accession)
    if slide_id:
        pat = pat.replace("{slideID}", slide_id)
    else:
        pat = pat.replace("{slideID}", "*")

    candidates = sorted(ann_dir.glob(pat))
    if not candidates:
        return None
    # Prefer .geojson first, then .json
    candidates_sorted = sorted(
        candidates,
        key=lambda p: (0 if p.suffix.lower() == ".geojson" else 1, len(p.name)),
    )
    return candidates_sorted[0]


def extract_class_name(props: Dict[str, Any]) -> str:
    """
    Robust class name extraction across common QuPath export variants.
    """
    # Direct keys
    for k in ("class", "name", "label", "type", "objectType"):
        v = props.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    # QuPath classification object
    cls = props.get("classification")
    if isinstance(cls, dict):
        v = cls.get("name") or cls.get("className")
        if isinstance(v, str) and v.strip():
            return v.strip()

    # Fallback
    return "unknown"


def iter_polygons_from_geojson(obj: Dict[str, Any]) -> Iterable[Tuple[str, List[List[Tuple[float, float]]]]]:
    """
    Yield (class_name, polygons) where polygons is a list of rings,
    and each ring is a list of (x, y) coords.
    For MultiPolygon, we yield multiple polygons.
    """
    if obj.get("type") != "FeatureCollection":
        return

    for feat in obj.get("features", []):
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties", {}) or {}
        geom = feat.get("geometry", {}) or {}
        if not isinstance(geom, dict):
            continue

        class_name = extract_class_name(props)

        gtype = geom.get("type")
        coords = geom.get("coordinates")

        if gtype == "Polygon" and isinstance(coords, list):
            # coords: [ring1, ring2, ...], ring: [[x,y],...]
            rings = []
            for ring in coords:
                if isinstance(ring, list):
                    rings.append([(float(x), float(y)) for x, y in ring if len([x, y]) == 2])
            if rings:
                yield (class_name, rings)

        elif gtype == "MultiPolygon" and isinstance(coords, list):
            # coords: [polygon1, polygon2, ...], polygon: [rings...]
            for poly in coords:
                rings = []
                if isinstance(poly, list):
                    for ring in poly:
                        if isinstance(ring, list):
                            rings.append([(float(x), float(y)) for x, y in ring if len([x, y]) == 2])
                if rings:
                    yield (class_name, rings)


def scale_ring(ring: List[Tuple[float, float]], sx: float, sy: float) -> List[Tuple[int, int]]:
    return [(int(round(x * sx)), int(round(y * sy))) for x, y in ring]


@dataclass
class OverlayAuditRow:
    accession_id: str
    slideID: str
    reduced_png: str
    ann_file: str
    full_width: Optional[int]
    full_height: Optional[int]
    reduced_width: Optional[int]
    reduced_height: Optional[int]
    sx: Optional[float]
    sy: Optional[float]
    n_features: int
    classes: str
    status: str


# -----------------------------
# Main
# -----------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Overlay annotation masks/ROIs onto reduced PNG previews.")
    ap.add_argument("--manifest", type=str, default="data/raw/H_glaber/manifest_raw.csv")
    ap.add_argument("--ann-dir", type=str, default="annotations/raw_exports")
    ap.add_argument(
        "--pattern",
        type=str,
        default="{accession}*.geojson",
        help="Glob pattern under ann-dir. Supports {accession} and {slideID}.",
    )
    ap.add_argument("--outdir", type=str, default="outputs/figures/overlays")
    ap.add_argument("--report-out", type=str, default="outputs/reports/overlay_audit.csv")
    ap.add_argument("--n", type=int, default=25, help="Number of accessions to sample")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--only-ok", action="store_true", help="Only use rows with ok==True")
    ap.add_argument("--alpha", type=int, default=80, help="Fill alpha for overlays (0-255)")
    ap.add_argument("--outline", type=int, default=2, help="Outline width (pixels)")
    ap.add_argument(
        "--full-width",
        type=int,
        default=None,
        help="Fallback full-res width for scaling if TIFF header not readable.",
    )
    ap.add_argument(
        "--full-height",
        type=int,
        default=None,
        help="Fallback full-res height for scaling if TIFF header not readable.",
    )
    args = ap.parse_args()

    root = repo_root()
    manifest_path = (root / args.manifest).resolve()
    ann_dir = (root / args.ann_dir).resolve()
    outdir = (root / args.outdir).resolve()
    report_out = (root / args.report_out).resolve()

    ensure_dir(outdir)
    ensure_dir(report_out.parent)

    if not manifest_path.exists():
        print(f"[ERROR] Missing manifest: {manifest_path}")
        print("Run: python explore/00_dataset_sanity.py")
        return 2

    df = pd.read_csv(manifest_path)

    if args.only_ok and "ok" in df.columns:
        df = df[df["ok"] == True]  # noqa: E712

    if df.empty:
        print("[ERROR] No rows available after filtering.")
        return 2

    if "reduced_png_path" not in df.columns:
        print("[ERROR] manifest missing reduced_png_path")
        return 2

    # Build candidates with existing reduced PNG
    candidates: List[pd.Series] = []
    for _, row in df.iterrows():
        rp = str(row.get("reduced_png_path", "")).strip()
        if not rp:
            continue
        p = Path(rp)
        if not p.is_absolute():
            p = (root / p).resolve()
        if p.exists():
            candidates.append(row)

    if not candidates:
        print("[ERROR] No existing reduced PNGs found from manifest.")
        return 2

    random.seed(args.seed)
    sample = candidates if len(candidates) <= args.n else random.sample(candidates, args.n)

    audits: List[OverlayAuditRow] = []

    for row in sample:
        accession = str(row.get("accession_id", "")).strip() or "unknown_accession"
        slide_id = str(row.get("slideID", "")).strip()
        reduced_path = Path(str(row.get("reduced_png_path", "")).strip())
        if not reduced_path.is_absolute():
            reduced_path = (root / reduced_path).resolve()

        ann_file = find_annotation_file(ann_dir, args.pattern, accession, slide_id if slide_id else None)

        # Load reduced image
        base = safe_read_image(reduced_path)
        if base is None:
            audits.append(
                OverlayAuditRow(
                    accession_id=accession,
                    slideID=slide_id,
                    reduced_png=str(reduced_path),
                    ann_file=str(ann_file) if ann_file else "",
                    full_width=None,
                    full_height=None,
                    reduced_width=None,
                    reduced_height=None,
                    sx=None,
                    sy=None,
                    n_features=0,
                    classes="",
                    status="reduced_unreadable",
                )
            )
            continue

        rw, rh = base.size

        if ann_file is None or not ann_file.exists():
            audits.append(
                OverlayAuditRow(
                    accession_id=accession,
                    slideID=slide_id,
                    reduced_png=str(reduced_path),
                    ann_file="",
                    full_width=None,
                    full_height=None,
                    reduced_width=rw,
                    reduced_height=rh,
                    sx=None,
                    sy=None,
                    n_features=0,
                    classes="",
                    status="missing_annotation_file",
                )
            )
            continue

        # Determine full-res dims
        full_w = None
        full_h = None

        tiff_path = str(row.get("tiff_path", "")).strip()
        if tiff_path:
            tp = Path(tiff_path)
            if not tp.is_absolute():
                tp = (root / tp).resolve()
            if tp.exists():
                dims = get_full_dims_from_tiff(tp)
                if dims:
                    full_w, full_h = dims

        if full_w is None or full_h is None:
            if args.full_width is not None and args.full_height is not None:
                full_w, full_h = args.full_width, args.full_height

        if full_w is None or full_h is None:
            audits.append(
                OverlayAuditRow(
                    accession_id=accession,
                    slideID=slide_id,
                    reduced_png=str(reduced_path),
                    ann_file=str(ann_file),
                    full_width=None,
                    full_height=None,
                    reduced_width=rw,
                    reduced_height=rh,
                    sx=None,
                    sy=None,
                    n_features=0,
                    classes="",
                    status="missing_full_dims",
                )
            )
            continue

        sx = rw / float(full_w)
        sy = rh / float(full_h)

        # Read GeoJSON
        try:
            obj = json.loads(ann_file.read_text(encoding="utf-8"))
        except Exception:
            audits.append(
                OverlayAuditRow(
                    accession_id=accession,
                    slideID=slide_id,
                    reduced_png=str(reduced_path),
                    ann_file=str(ann_file),
                    full_width=full_w,
                    full_height=full_h,
                    reduced_width=rw,
                    reduced_height=rh,
                    sx=sx,
                    sy=sy,
                    n_features=0,
                    classes="",
                    status="annotation_unreadable_json",
                )
            )
            continue

        # Create overlay layer
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        n_features = 0
        class_set: List[str] = []

        for class_name, rings in iter_polygons_from_geojson(obj) or []:
            n_features += 1
            class_set.append(class_name)
            rgb = deterministic_color(class_name)
            fill = (rgb[0], rgb[1], rgb[2], int(max(0, min(255, args.alpha))))
            outline = (rgb[0], rgb[1], rgb[2], 255)

            # Draw exterior ring; ignore holes for now (simple + robust for EDA)
            exterior = rings[0] if rings else []
            if len(exterior) < 3:
                continue
            pts = scale_ring(exterior, sx, sy)

            # PIL's polygon fill and outline
            try:
                draw.polygon(pts, fill=fill, outline=outline)
                # Thicken outline by re-drawing (simple approximation)
                for _ in range(max(0, args.outline - 1)):
                    draw.line(pts + [pts[0]], fill=outline, width=2)
            except Exception:
                continue

        # Composite and save
        comp = Image.alpha_composite(base, overlay).convert("RGB")
        out_path = outdir / f"{accession}_overlay.png"
        comp.save(out_path, quality=95)

        classes_sorted = ",".join(sorted(set(class_set), key=lambda x: normalize_key(x)))
        status = "ok" if n_features > 0 else "no_polygons_found"

        audits.append(
            OverlayAuditRow(
                accession_id=accession,
                slideID=slide_id,
                reduced_png=str(reduced_path),
                ann_file=str(ann_file),
                full_width=full_w,
                full_height=full_h,
                reduced_width=rw,
                reduced_height=rh,
                sx=sx,
                sy=sy,
                n_features=n_features,
                classes=classes_sorted,
                status=status,
            )
        )

    # Write audit report
    audit_df = pd.DataFrame([a.__dict__ for a in audits])
    audit_df.to_csv(report_out, index=False)

    print("\nEDA: Overlay Masks Summary")
    print("=========================")
    print(f"Manifest: {manifest_path}")
    print(f"Annotation dir: {ann_dir}")
    print(f"Outdir: {outdir}")
    print(f"Report: {report_out}")
    print(f"tifffile available: {tifffile is not None}")
    print("\nStatus counts:")
    print(audit_df["status"].value_counts(dropna=False).to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
