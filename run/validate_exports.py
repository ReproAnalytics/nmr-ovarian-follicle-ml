#!/usr/bin/env python3
# Code debugging facilitated by ChatGPT (GPT 5.2 Instant)

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import load_config
from src.utils.paths import find_repo_root


def _pick_col(cols: list[str], candidates: list[str], required: bool = True) -> str | None:
    """
    Return the first matching column name from candidates, case-insensitive.
    """
    normalized = {c.strip().lower(): c for c in cols}
    for cand in candidates:
        hit = normalized.get(cand.strip().lower())
        if hit is not None:
            return hit
    if required:
        raise ValueError(f"Could not find any of columns {candidates} in {cols}")
    return None


def _normalize_label(label: str) -> str:
    """
    Normalize label text for matching against labelmap keys.
    """
    return label.strip().lower().replace(" ", "_").replace("-", "_")


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _resolve_path(value: str, repo: Path) -> Path:
    """
    Resolve a path from CSV/config relative to repo root unless already absolute.
    """
    p = Path(value.strip())
    if p.is_absolute():
        return p.resolve()
    return (repo / p).resolve()


def _candidate_path_strings(path_value: str, repo: Path) -> set[str]:
    """
    Build multiple normalized string variants for matching a tile path found in
    QuPath exports against the tiles_manifest.
    """
    raw = path_value.strip()
    if not raw:
        return set()

    out: set[str] = set()

    # raw forms
    out.add(raw)
    out.add(raw.replace("\\", "/"))

    p = Path(raw)

    # absolute path if resolvable relative to repo
    try:
        resolved = _resolve_path(raw, repo)
        out.add(str(resolved))
        out.add(resolved.as_posix())

        # path relative to repo root
        try:
            rel = resolved.relative_to(repo.resolve())
            out.add(str(rel))
            out.add(rel.as_posix())
        except ValueError:
            pass

        # basename
        out.add(resolved.name)
    except Exception:
        pass

    # basename from raw
    out.add(p.name)

    return {x for x in out if x}


def _load_labelmap(path: Path) -> tuple[dict[str, int], dict[str, str]]:
    """
    Returns:
      canonical_label_to_id
      normalized_label_to_canonical
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError(f"labelmap must be a non-empty JSON object: {path}")

    canonical_to_id: dict[str, int] = {}
    normalized_to_canonical: dict[str, str] = {}

    for k, v in data.items():
        canonical = str(k).strip()
        canonical_to_id[canonical] = int(v)
        normalized_to_canonical[_normalize_label(canonical)] = canonical

    return canonical_to_id, normalized_to_canonical


def _load_tiles_manifest(manifest_path: Path, repo: Path) -> tuple[set[str], dict[str, str]]:
    """
    Load tiles_manifest and build:
      - valid tile paths (canonical absolute posix strings)
      - alias -> canonical mapping for flexible matching

    Expected manifest contains at least one tile path-like column.
    """
    rows = _read_csv_rows(manifest_path)
    if not rows:
        raise SystemExit(f"tiles_manifest is empty: {manifest_path}")

    cols = list(rows[0].keys())
    tile_col = _pick_col(
        cols,
        [
            "tile_path",
            "path",
            "tile",
            "image",
            "image_path",
            "filepath",
            "file_path",
            "png_path",
        ],
        required=True,
    )

    canonical_tiles: set[str] = set()
    alias_to_canonical: dict[str, str] = {}

    for row in rows:
        raw_tile = (row.get(tile_col) or "").strip()
        if not raw_tile:
            continue

        canonical_path = _resolve_path(raw_tile, repo).as_posix()
        canonical_tiles.add(canonical_path)

        aliases = _candidate_path_strings(raw_tile, repo)
        aliases.add(canonical_path)
        aliases.add(Path(canonical_path).name)

        try:
            rel = Path(canonical_path).relative_to(repo.resolve()).as_posix()
            aliases.add(rel)
        except Exception:
            pass

        for alias in aliases:
            alias_to_canonical[alias] = canonical_path

    if not canonical_tiles:
        raise SystemExit(f"No valid tile paths found in tiles_manifest: {manifest_path}")

    return canonical_tiles, alias_to_canonical


def _find_matching_manifest_tile(
    exported_tile_value: str,
    repo: Path,
    alias_to_canonical: dict[str, str],
) -> str | None:
    """
    Try to match a tile reference from a QuPath export to a tile listed in tiles_manifest.
    """
    for alias in _candidate_path_strings(exported_tile_value, repo):
        hit = alias_to_canonical.get(alias)
        if hit is not None:
            return hit
    return None


def _iter_export_csvs(raw_exports_dir: Path) -> Iterable[Path]:
    return sorted(raw_exports_dir.glob("*.csv"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Consolidate QuPath annotation CSV exports into a training-ready labels CSV."
    )
    ap.add_argument("--config", default="configs/annotate.yaml")
    args = ap.parse_args()

    repo = find_repo_root()
    cfg = load_config(repo / args.config)

    paths_cfg = cfg["paths"]
    annotate_cfg = cfg.get("annotate", {})

    raw_exports_dir = repo / paths_cfg["raw_exports"]
    labelmap_path = repo / paths_cfg["labelmap"]
    gold_out = repo / paths_cfg["gold_set"]
    tiles_manifest_path = repo / paths_cfg["tiles_manifest"]

    if not raw_exports_dir.exists():
        raise SystemExit(f"raw_exports directory not found: {raw_exports_dir}")
    if not labelmap_path.exists():
        raise SystemExit(f"labelmap file not found: {labelmap_path}")
    if not tiles_manifest_path.exists():
        raise SystemExit(f"tiles_manifest file not found: {tiles_manifest_path}")

    strategy = str(annotate_cfg.get("strategy", "majority_vote")).strip()
    min_agreement = int(annotate_cfg.get("min_agreement", 1))

    if strategy not in {"majority_vote", "expert_override"}:
        raise SystemExit(
            f"Unsupported annotate.strategy={strategy!r}. "
            "Expected one of: majority_vote, expert_override"
        )

    canonical_to_id, normalized_to_canonical = _load_labelmap(labelmap_path)
    valid_tiles, alias_to_canonical = _load_tiles_manifest(tiles_manifest_path, repo)

    export_files = list(_iter_export_csvs(raw_exports_dir))
    if not export_files:
        raise SystemExit(f"No CSV exports found in {raw_exports_dir}")

    # votes[canonical_tile_path] = list of vote records
    votes: dict[str, list[dict[str, str]]] = defaultdict(list)

    n_rows_total = 0
    n_rows_missing_fields = 0
    n_rows_unknown_label = 0
    n_rows_unmatched_tile = 0
    n_rows_valid = 0

    for export_path in export_files:
        rows = _read_csv_rows(export_path)
        if not rows:
            continue

        cols = list(rows[0].keys())

        tile_col = _pick_col(
            cols,
            [
                "tile_path",
                "tile",
                "path",
                "image",
                "image path",
                "image_path",
                "filepath",
                "file_path",
                "name",
            ],
            required=True,
        )

        label_col = _pick_col(
            cols,
            [
                "label",
                "classification",
                "class",
                "class name",
                "classification name",
                "object class",
            ],
            required=True,
        )

        annotator_col = _pick_col(
            cols,
            [
                "annotator",
                "reviewer",
                "user",
                "author",
                "created_by",
                "modified_by",
            ],
            required=False,
        )

        is_expert_col = _pick_col(
            cols,
            [
                "is_expert",
                "expert",
                "adjudicated",
                "override",
            ],
            required=False,
        )

        for row in rows:
            n_rows_total += 1

            raw_tile = (row.get(tile_col) or "").strip()
            raw_label = (row.get(label_col) or "").strip()

            if not raw_tile or not raw_label:
                n_rows_missing_fields += 1
                continue

            normalized_label = _normalize_label(raw_label)
            canonical_label = normalized_to_canonical.get(normalized_label)
            if canonical_label is None:
                n_rows_unknown_label += 1
                continue

            matched_tile = _find_matching_manifest_tile(raw_tile, repo, alias_to_canonical)
            if matched_tile is None or matched_tile not in valid_tiles:
                n_rows_unmatched_tile += 1
                continue

            annotator = ""
            if annotator_col is not None:
                annotator = (row.get(annotator_col) or "").strip()

            is_expert = ""
            if is_expert_col is not None:
                is_expert = (row.get(is_expert_col) or "").strip().lower()

            votes[matched_tile].append(
                {
                    "label": canonical_label,
                    "source_file": export_path.name,
                    "annotator": annotator,
                    "is_expert": is_expert,
                }
            )
            n_rows_valid += 1

    if not votes:
        raise SystemExit(
            "No valid annotations remained after label normalization and "
            "tiles_manifest validation. Check your QuPath export columns, "
            "labelmap.json, and tiles_manifest paths."
        )

    out_rows: list[dict[str, str | int]] = []

    for tile_path in sorted(votes.keys()):
        entries = votes[tile_path]
        labels = [e["label"] for e in entries]
        counts = Counter(labels)

        chosen_label: str | None = None

        if strategy == "expert_override":
            # Prefer explicitly expert/adjudicated rows if present.
            expert_entries = [
                e for e in entries
                if e["is_expert"] in {"1", "true", "yes", "y"}
            ]
            if expert_entries:
                expert_counts = Counter(e["label"] for e in expert_entries)
                chosen_label, _ = expert_counts.most_common(1)[0]
            else:
                chosen_label, top_votes = counts.most_common(1)[0]
                if top_votes < min_agreement:
                    continue

        elif strategy == "majority_vote":
            chosen_label, top_votes = counts.most_common(1)[0]
            if top_votes < min_agreement:
                continue

        if chosen_label is None:
            continue

        out_rows.append(
            {
                "tile_path": tile_path,
                "label": chosen_label,
                "label_id": canonical_to_id[chosen_label],
                "source_file": ";".join(sorted({e["source_file"] for e in entries})),
                "annotator": ";".join(sorted({e["annotator"] for e in entries if e["annotator"]})),
                "n_votes": len(entries),
                "n_unique_votes": len(counts),
            }
        )

    if not out_rows:
        raise SystemExit(
            "All annotation rows were filtered out. "
            "This usually means min_agreement is too high for the current exports."
        )

    gold_out.parent.mkdir(parents=True, exist_ok=True)
    with gold_out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "tile_path",
                "label",
                "label_id",
                "source_file",
                "annotator",
                "n_votes",
                "n_unique_votes",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"[annotate] config: {repo / args.config}")
    print(f"[annotate] raw exports: {raw_exports_dir}")
    print(f"[annotate] tiles manifest: {tiles_manifest_path}")
    print(f"[annotate] labelmap: {labelmap_path}")
    print(f"[annotate] strategy={strategy} min_agreement={min_agreement}")
    print(f"[annotate] export files read: {len(export_files)}")
    print(f"[annotate] rows scanned: {n_rows_total}")
    print(f"[annotate] rows missing tile/label: {n_rows_missing_fields}")
    print(f"[annotate] rows with unknown labels: {n_rows_unknown_label}")
    print(f"[annotate] rows unmatched to tiles_manifest: {n_rows_unmatched_tile}")
    print(f"[annotate] valid annotation rows: {n_rows_valid}")
    print(f"[annotate] labeled training rows written: {len(out_rows)}")
    print(f"[annotate] output: {gold_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
