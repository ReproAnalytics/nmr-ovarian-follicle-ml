#!/usr/bin/env python3
"""
explore/00_dataset_sanity.py

Purpose: Validate raw dataset layout and extract metadata from MOTHER XML.

Expected layout:
  data/raw/H_glaber/<accession_id>/
    - one *.tif / *.tiff  
    - one *.xml           
    - one *_reduced.png
    - one *_thumbnail.png

Outputs:
  - data/raw/H_glaber/manifest_raw.csv                  # pipeline-facing 
  - outputs/reports/dataset_inventory.csv               # EDA/report-facing 
  - outputs/reports/dataset_inventory_with_paths.csv    # debug copy with paths, for troubleshooting
  - outputs/metrics/dataset_sanity.json                 # summary + completeness + issue/warning counts

Run from repo root:
  python explore/00_dataset_sanity.py
  python explore/00_dataset_sanity.py --raw-root data/raw/H_glaber
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Optional TIFF header 
try:
    import tifffile  # type: ignore
except Exception:
    tifffile = None


TIFF_EXTS = (".tif", ".tiff")
XML_EXT = ".xml"
EXPECTED_PNG_SUFFIXES = ("_reduced.png", "_thumbnail.png")

# Columns to remove from exported CSVs
DROP_FROM_EXPORT = [
    "donor_dir",
    "tiff_path",
    "xml_path",
    "reduced_png_path",
    "thumbnail_png_path",
]

# ---- XML parsing (MOTHER) --------------------------------

NS = {
    "eml": "https://eml.ecoinformatics.org/eml-2.2.0",
    "mdb": "http://mother-db.org/mdb",
}


def _tag_local(tag: str) -> str:
    """'{ns}name' -> 'name'"""
    return tag.split("}")[-1] if "}" in tag else tag


def _text_or_none(el: Optional[ET.Element]) -> Optional[str]:
    if el is None or el.text is None:
        return None
    s = el.text.strip()
    return s if s else None


def _to_int_or_none(x: Optional[str]) -> Optional[int]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def parse_mother_xml(xml_path: Path) -> Dict[str, Optional[str]]:
    """
    Parse the MOTHER XML (EML) and extract metadata under <mdb:mother>.

    Returns a flat dict. Missing fields are None.
    """
    out: Dict[str, Optional[str]] = {
        # IDs
        "xml_packageId": None,
        "xml_dataset_title": None,
        "donorID": None,
        "slideID": None,
        # donor
        "donorSex": None,
        "donorLifeStage": None,
        "donorAge": None,     # normalized string
        "donorDays": None,    # raw string
        "donorYears": None,   # raw string
        # specimen
        "specimenTissue": None,
        "specimenLocation": None,
        "ovaryPosition": None,
        "wholeOvary": None,
        "specimenCycle": None,
        # processing / imaging
        "fixation": None,
        "stain_type": None,
        "magnification": None,
        "microscope_model": None,
        "sectionThickness": None,
        # free-text
        "notes": None,
    }

    tree = ET.parse(xml_path)
    root = tree.getroot()

    out["xml_packageId"] = root.attrib.get("packageId")

    title_el = root.find(".//eml:dataset/eml:title", NS)
    out["xml_dataset_title"] = _text_or_none(title_el)

    mother = root.find(".//mdb:mother", NS)
    if mother is None:
        return out

    def t(rel_path: str) -> Optional[str]:
        return _text_or_none(mother.find(rel_path, NS))

    # Direct fields under <mdb:mother>
    out["donorID"] = t("mdb:donorID")
    out["slideID"] = t("mdb:slideID")
    out["donorSex"] = t("mdb:donorSex")
    out["donorLifeStage"] = t("mdb:donorLifeStage")

    out["specimenTissue"] = t("mdb:specimenTissue")
    out["specimenLocation"] = t("mdb:specimenLocation")
    out["ovaryPosition"] = t("mdb:ovaryPosition")
    out["wholeOvary"] = t("mdb:wholeOvary")
    out["specimenCycle"] = t("mdb:specimenCycle")

    out["notes"] = t("mdb:notes")

    # donorAge is a container in your XML (nested donorYears/donorDays)
    donor_age_el = mother.find("mdb:donorAge", NS)
    if donor_age_el is not None:
        out["donorYears"] = _text_or_none(donor_age_el.find("mdb:donorYears", NS))
        out["donorDays"] = _text_or_none(donor_age_el.find("mdb:donorDays", NS))
    else:
        # fallback for variants where donorDays/Years appear elsewhere
        out["donorYears"] = _text_or_none(mother.find(".//mdb:donorYears", NS))
        out["donorDays"] = _text_or_none(mother.find(".//mdb:donorDays", NS))

    # Normalize donorAge to include total days 
    yrs_i = _to_int_or_none(out["donorYears"])
    dys_i = _to_int_or_none(out["donorDays"])
    if yrs_i is not None or dys_i is not None:
        yrs_i = yrs_i or 0
        dys_i = dys_i or 0
        total_days = yrs_i * 365 + dys_i
        out["donorAge"] = f"{yrs_i} years {dys_i} days ({total_days} days)"
    else:
        # fallback if donorAge is simple text in other variants
        out["donorAge"] = t("mdb:donorAge")

    # Fixation: nested structure, capture first child tag
    fixation_el = mother.find(".//mdb:fixation", NS)
    if fixation_el is not None:
        kids = list(fixation_el)
        if kids:
            out["fixation"] = _tag_local(kids[0].tag)

    # Stain: capture first stain type under lightMicroscopyStain
    stain_el = mother.find(".//mdb:stain", NS)
    if stain_el is not None:
        lm = stain_el.find(".//mdb:lightMicroscopyStain", NS)
        if lm is not None:
            lm_kids = list(lm)
            if lm_kids:
                out["stain_type"] = _tag_local(lm_kids[0].tag)

    # Magnification: prefer text; fallback to attribute
    mag_el = mother.find("mdb:magnification", NS)
    mag_txt = _text_or_none(mag_el)
    if mag_txt:
        out["magnification"] = mag_txt
    elif mag_el is not None:
        for attr_key in ("value", "magnification", "mag"):
            if attr_key in mag_el.attrib and mag_el.attrib[attr_key].strip():
                out["magnification"] = mag_el.attrib[attr_key].strip()
                break

    # Microscope model (nested)
    mm = mother.find(".//mdb:microscope/mdb:model", NS)
    out["microscope_model"] = _text_or_none(mm) or _text_or_none(mother.find(".//mdb:model", NS))

    # Section thickness
    sec = mother.find(".//mdb:sectionThickness", NS)
    if sec is not None:
        thick = sec.findtext(".//mdb:thickness", default="", namespaces=NS).strip()
        unit = sec.findtext(".//mdb:unit", default="", namespaces=NS).strip()
        if thick or unit:
            out["sectionThickness"] = f"{thick} {unit}".strip()

    return out


# ---- Filesystem scanning -----------------------------------------------------

@dataclass
class DonorRow:
    accession_id: str
    donor_dir: str

    tiff_path: str
    xml_path: str
    reduced_png_path: str
    thumbnail_png_path: str

    ok: bool
    issues: List[str]
    warnings: List[str]

    # Debug: list any extra TIFF/XML candidates
    tiff_candidates: str = ""
    xml_candidates: str = ""

    # sizes (bytes)
    tiff_size: Optional[int] = None
    xml_size: Optional[int] = None
    reduced_png_size: Optional[int] = None
    thumbnail_png_size: Optional[int] = None

    # TIFF header hints (optional)
    tiff_pages: Optional[int] = None
    tiff_series_count: Optional[int] = None
    tiff_is_ome: Optional[bool] = None
    tiff_shape_hint: Optional[str] = None

    # XML extracted fields
    xml_packageId: Optional[str] = None
    xml_dataset_title: Optional[str] = None
    donorID: Optional[str] = None
    slideID: Optional[str] = None
    donorSex: Optional[str] = None
    donorLifeStage: Optional[str] = None
    donorAge: Optional[str] = None
    donorDays: Optional[str] = None
    donorYears: Optional[str] = None
    specimenTissue: Optional[str] = None
    specimenLocation: Optional[str] = None
    ovaryPosition: Optional[str] = None
    wholeOvary: Optional[str] = None
    specimenCycle: Optional[str] = None
    fixation: Optional[str] = None
    stain_type: Optional[str] = None
    magnification: Optional[str] = None
    microscope_model: Optional[str] = None
    sectionThickness: Optional[str] = None
    notes: Optional[str] = None


def find_single_file(folder: Path, exts: Tuple[str, ...]) -> Tuple[Optional[Path], List[Path]]:
    hits: List[Path] = []
    for ext in exts:
        hits.extend(folder.glob(f"*{ext}"))
    hits = sorted(set(hits))
    if len(hits) == 1:
        return hits[0], hits
    return None, hits


def find_png_by_suffix(folder: Path, suffix: str) -> Optional[Path]:
    hits = sorted(folder.glob(f"*{suffix}"))
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    # choose shortest filename if multiple
    return sorted(hits, key=lambda p: len(p.name))[0]


def tiff_quickcheck(tiff_path: Path) -> Dict[str, Optional[object]]:
    info: Dict[str, Optional[object]] = {
        "tiff_pages": None,
        "tiff_series_count": None,
        "tiff_is_ome": None,
        "tiff_shape_hint": None,
    }
    if tifffile is None:
        return info

    try:
        with tifffile.TiffFile(str(tiff_path)) as tf:
            info["tiff_pages"] = len(tf.pages)
            info["tiff_series_count"] = len(tf.series)
            info["tiff_is_ome"] = bool(tf.ome_metadata is not None)
            if tf.series:
                info["tiff_shape_hint"] = str(getattr(tf.series[0], "shape", None))
    except Exception:
        return info

    return info


def normalize_for_match(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def scan_donor_folder(donor_dir: Path) -> DonorRow:
    warnings: List[str] = []
    accession_id = donor_dir.name
    issues: List[str] = []

    tiff_path, tiff_hits = find_single_file(donor_dir, TIFF_EXTS)
    xml_path, xml_hits = find_single_file(donor_dir, (XML_EXT,))
    reduced_png = find_png_by_suffix(donor_dir, EXPECTED_PNG_SUFFIXES[0])
    thumbnail_png = find_png_by_suffix(donor_dir, EXPECTED_PNG_SUFFIXES[1])

    if tiff_path is None:
        issues.append("missing_tiff" if len(tiff_hits) == 0 else f"multiple_tiffs({len(tiff_hits)})")
    if xml_path is None:
        issues.append("missing_xml" if len(xml_hits) == 0 else f"multiple_xmls({len(xml_hits)})")
    if reduced_png is None:
        issues.append("missing_reduced_png")
    if thumbnail_png is None:
        issues.append("missing_thumbnail_png")

    row = DonorRow(
        accession_id=accession_id,
        donor_dir=str(donor_dir.as_posix()),
        tiff_path=str(tiff_path.as_posix()) if tiff_path else "",
        xml_path=str(xml_path.as_posix()) if xml_path else "",
        reduced_png_path=str(reduced_png.as_posix()) if reduced_png else "",
        thumbnail_png_path=str(thumbnail_png.as_posix()) if thumbnail_png else "",
        ok=len(issues) == 0,
        issues=issues,
        warnings=warnings,
        tiff_candidates=";".join([p.name for p in tiff_hits]),
        xml_candidates=";".join([p.name for p in xml_hits]),
    )

    # TIFF sizes + header hints
    if tiff_path and tiff_path.exists():
        row.tiff_size = tiff_path.stat().st_size
        qc = tiff_quickcheck(tiff_path)
        row.tiff_pages = qc.get("tiff_pages")  # type: ignore
        row.tiff_series_count = qc.get("tiff_series_count")  # type: ignore
        row.tiff_is_ome = qc.get("tiff_is_ome")  # type: ignore
        row.tiff_shape_hint = qc.get("tiff_shape_hint")  # type: ignore
        if tifffile is not None and row.tiff_pages is None:
            row.issues.append("tiff_unreadable_header")

    # XML sizes + metadata extraction
    if xml_path and xml_path.exists():
        row.xml_size = xml_path.stat().st_size
        try:
            meta = parse_mother_xml(xml_path)
            for k, v in meta.items():
                setattr(row, k, v)
        except Exception as e:
            row.issues.append(f"xml_parse_error({e.__class__.__name__})")

        # Validate that mdb block exists (donorID/slideID are good proxies)
        if row.donorID is None and row.slideID is None:
            row.issues.append("xml_missing_mdb_mother_block")

        # Filename consistency checks using slideID / donorID if present (warnings only)
        fnames = " ".join([p.name for p in donor_dir.iterdir() if p.is_file()]).lower()
        fn_norm = normalize_for_match(fnames)

        if row.slideID:
            slide_norm = normalize_for_match(row.slideID)
            if slide_norm and slide_norm not in fn_norm:
                row.warnings.append("slideID_not_in_filenames")

        if row.donorID:
            donor_norm = normalize_for_match(row.donorID)
            if donor_norm and donor_norm not in fn_norm:
                row.warnings.append("donorID_not_in_filenames")

    if reduced_png and reduced_png.exists():
        row.reduced_png_size = reduced_png.stat().st_size
    if thumbnail_png and thumbnail_png.exists():
        row.thumbnail_png_size = thumbnail_png.stat().st_size

    # ok iff no issues
    row.ok = len(row.issues) == 0
    return row


# ---- Summary + I/O -----------------------------------------------------------

def ensure_parent_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def summarize(rows: List[DonorRow]) -> Dict[str, object]:
    total = len(rows)
    ok = sum(1 for r in rows if r.ok)
    bad = total - ok

    issue_counts: Dict[str, int] = {}
    warning_counts: Dict[str, int] = {}

    for r in rows:
        for issue in r.issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        for w in r.warnings:
            warning_counts[w] = warning_counts.get(w, 0) + 1

    def completeness(field: str) -> Dict[str, int]:
        present = sum(1 for r in rows if getattr(r, field) not in (None, ""))
        return {"present": present, "missing": total - present}

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "total_accessions": total,
        "ok_accessions": ok,
        "bad_accessions": bad,
        "tifffile_available": tifffile is not None,
        "issue_counts": dict(sorted(issue_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "warning_counts": dict(sorted(warning_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "xml_field_completeness": {
            "donorID": completeness("donorID"),
            "slideID": completeness("slideID"),
            "donorSex": completeness("donorSex"),
            "donorLifeStage": completeness("donorLifeStage"),
            "donorAge": completeness("donorAge"),
            "donorYears": completeness("donorYears"),
            "donorDays": completeness("donorDays"),
            "specimenTissue": completeness("specimenTissue"),
            "ovaryPosition": completeness("ovaryPosition"),
            "stain_type": completeness("stain_type"),
            "magnification": completeness("magnification"),
            "sectionThickness": completeness("sectionThickness"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Dataset sanity checks + XML-driven metadata extraction.")
    parser.add_argument(
        "--raw-root",
        type=str,
        default="data/raw/H_glaber",
        help="Path to raw root containing accession folders (default: data/raw/H_glaber)",
    )
    parser.add_argument(
        "--manifest-out",
        type=str,
        default="data/raw/H_glaber/manifest_raw.csv",
        help="Canonical manifest output (pipeline-facing) [paths removed per request]",
    )
    parser.add_argument(
        "--inventory-out",
        type=str,
        default="outputs/reports/dataset_inventory.csv",
        help="EDA/reporting inventory copy [paths removed per request]",
    )
    parser.add_argument(
        "--inventory-with-paths-out",
        type=str,
        default="outputs/reports/dataset_inventory_with_paths.csv",
        help="Debug inventory copy WITH file paths (recommended for troubleshooting)",
    )
    parser.add_argument(
        "--metrics-out",
        type=str,
        default="outputs/metrics/dataset_sanity.json",
        help="Output path for JSON metrics",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    raw_root = (repo_root / args.raw_root).resolve()

    if not raw_root.exists():
        print(f"[ERROR] raw-root does not exist: {raw_root}", file=sys.stderr)
        return 2

    donor_dirs = sorted([p for p in raw_root.iterdir() if p.is_dir()])
    if not donor_dirs:
        print(f"[ERROR] No accession folders found under: {raw_root}", file=sys.stderr)
        return 2

    rows: List[DonorRow] = [scan_donor_folder(d) for d in donor_dirs]
    df_full = pd.DataFrame([asdict(r) for r in rows])

    # Create donorAgeDays column for inventory export
    donorYears_num = pd.to_numeric(df_full.get("donorYears"), errors="coerce").fillna(0)
    donorDays_num = pd.to_numeric(df_full.get("donorDays"), errors="coerce").fillna(0)

    donorAgeDays = donorDays_num + donorYears_num * 365

    if "donorAge" in df_full.columns:
        insert_at = df_full.columns.get_loc("donorAge") + 1
        df_full.insert(insert_at, "donorAgeDays", donorAgeDays)
    else:
        df_full["donorAgeDays"] = donorAgeDays


    # Export versions (paths removed)
    df_export = df_full.drop(columns=[c for c in DROP_FROM_EXPORT if c in df_full.columns])

    # 1) Canonical manifest (pipeline) [paths removed]
    manifest_path = (repo_root / args.manifest_out).resolve()
    ensure_parent_dir(manifest_path)
    df_export.to_csv(manifest_path, index=False)

    # 2) EDA/report inventory copy [paths removed]
    inventory_path = (repo_root / args.inventory_out).resolve()
    ensure_parent_dir(inventory_path)
    df_export.to_csv(inventory_path, index=False)

    # 2b) Debug inventory with paths (helps if something breaks later)
    inventory_with_paths_path = (repo_root / args.inventory_with_paths_out).resolve()
    ensure_parent_dir(inventory_with_paths_path)
    df_full.to_csv(inventory_with_paths_path, index=False)

    # 3) Metrics summary JSON
    metrics = summarize(rows)
    metrics_path = (repo_root / args.metrics_out).resolve()
    ensure_parent_dir(metrics_path)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # Console report
    print("\nDataset Sanity Summary (XML-driven)")
    print("==================================")
    print(f"Raw root: {raw_root}")
    print(f"Accessions found: {metrics['total_accessions']}")
    print(f"OK: {metrics['ok_accessions']}   Bad: {metrics['bad_accessions']}")
    print(f"tifffile available: {metrics['tifffile_available']}")

    if metrics["issue_counts"]:
        print("\nTop issues:")
        for k, v in metrics["issue_counts"].items():
            print(f"  {k}: {v}")

    if metrics["warning_counts"]:
        print("\nTop warnings:")
        for k, v in metrics["warning_counts"].items():
            print(f"  {k}: {v}")

    print("\nXML field completeness:")
    for field, stats in metrics["xml_field_completeness"].items():
        print(f"  {field}: present={stats['present']} missing={stats['missing']}")

    print("\nWrote:")
    print(f"  - {manifest_path} ")
    print(f"  - {inventory_path} ")
    print(f"  - {inventory_with_paths_path} (debug, includes paths)")
    print(f"  - {metrics_path}")

    # Exit non-zero if any bad accessions (useful for CI)
    return 0 if metrics["bad_accessions"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
