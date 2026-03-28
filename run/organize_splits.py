#!/usr/bin/env python3
"""
Organize labeled tiles into train/valid/test folder structure for CNN training.

Reads annotations/gold_set/labeled_tiles.csv, splits by accession
(to avoid data leakage), and symlinks or copies tiles into:

    data/processed/H_glaber/
        train/<label>/
        valid/<label>/
        test/<label>/

Debugging and code assistance were provided by Claude (Opus 4.6)
"""
from __future__ import annotations

import argparse
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.paths import find_repo_root
from src.utils.io import read_csv_rows
from src.utils.logging import make_logger, now_stamp


def _normalize_label_dir(label: str) -> str:
    """Lowercase, replace spaces/hyphens with underscores for folder names."""
    return label.strip().lower().replace(" ", "_").replace("-", "_")


def _extract_accession(tile_path: str) -> str:
    """
    Derive the accession ID from a tile path.
    Expects accession to appear as a path component, e.g.
    .../tiles/ACC_001/tile_0001.png  ->  ACC_001
    """
    parts = Path(tile_path).parts
    # Walk backwards to find a component that looks like an accession
    # Heuristic: first directory component above the filename
    if len(parts) >= 2:
        return parts[-2]
    return "unknown"


def organize(
    gold_csv: Path,
    output_root: Path,
    train_ratio: float,
    valid_ratio: float,
    seed: int,
    use_symlinks: bool,
    log,
) -> None:
    rows = read_csv_rows(gold_csv)
    if not rows:
        raise SystemExit(f"Gold set is empty: {gold_csv}")

    log(f"Loaded {len(rows)} labeled tiles from {gold_csv}", prefix="splits")

    # Group tiles by accession
    accession_tiles: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        acc = _extract_accession(r["tile_path"])
        accession_tiles[acc].append(r)

    accessions = sorted(accession_tiles.keys())
    log(f"Found {len(accessions)} accessions: {accessions}", prefix="splits")

    # Shuffle and split accessions (not individual tiles)
    rng = random.Random(seed)
    rng.shuffle(accessions)

    n = len(accessions)
    n_train = max(1, int(n * train_ratio))
    n_valid = max(1, int(n * valid_ratio))
    # Remaining go to test; if only 1-2 accessions, test may be empty
    train_accs = accessions[:n_train]
    valid_accs = accessions[n_train : n_train + n_valid]
    test_accs = accessions[n_train + n_valid :]

    split_map = {}
    for acc in train_accs:
        split_map[acc] = "train"
    for acc in valid_accs:
        split_map[acc] = "valid"
    for acc in test_accs:
        split_map[acc] = "test"

    log(f"Split: train={train_accs}, valid={valid_accs}, test={test_accs}", prefix="splits")

    # Clean output directory
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = defaultdict(int)

    for acc, tiles in accession_tiles.items():
        split = split_map[acc]
        for r in tiles:
            label_dir = _normalize_label_dir(r["label"])
            dest_dir = output_root / split / label_dir
            dest_dir.mkdir(parents=True, exist_ok=True)

            src = Path(r["tile_path"])
            dest = dest_dir / src.name

            if use_symlinks:
                # Absolute symlink so it works regardless of cwd
                dest.symlink_to(src.resolve())
            else:
                shutil.copy2(src, dest)

            counts[split] += 1

    for split in ("train", "valid", "test"):
        log(f"  {split}: {counts.get(split, 0)} tiles", prefix="splits")

    log(f"Output root: {output_root}", prefix="splits")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Organize labeled tiles into train/valid/test folder structure."
    )
    parser.add_argument("--gold-csv", default="annotations/gold_set/labeled_tiles.csv")
    parser.add_argument("--output", default="data/processed/H_glaber")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--valid-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--copy", action="store_true",
        help="Copy files instead of creating symlinks.",
    )
    args = parser.parse_args()

    repo = find_repo_root(Path.cwd())
    log = make_logger(repo / f"outputs/logs/organize_splits_{now_stamp()}.log")

    gold_csv = repo / args.gold_csv
    output_root = repo / args.output

    if not gold_csv.exists():
        raise SystemExit(f"Gold set not found: {gold_csv}")

    log("ORGANIZE SPLITS STAGE", prefix="splits")

    organize(
        gold_csv=gold_csv,
        output_root=output_root,
        train_ratio=args.train_ratio,
        valid_ratio=args.valid_ratio,
        seed=args.seed,
        use_symlinks=not args.copy,
        log=log,
    )

    log("ORGANIZE SPLITS COMPLETE", prefix="splits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())