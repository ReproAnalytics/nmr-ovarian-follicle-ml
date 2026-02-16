#!/usr/bin/env python3
"""
Training stage entry point.

Inputs:
- tiles manifest CSV (expected columns include: slide_path, tile_path, ... and ideally label)

Outputs:
- split manifests in data/processed/
- a run directory in outputs/models/<run_name>/ (or configured path)
- logs in outputs/logs/

NB: Adjust code when QuPath output format is established.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


# -----------------------------
# Logging (simple, file-backed)
# -----------------------------
def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def make_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        line = f"[train] {msg}"
        print(line)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")

    return log


# -----------------------------
# Manifest I/O
# -----------------------------
def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Tiles manifest not found: {path}")

    with path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        rows = [dict(r) for r in reader]
    return rows


def write_csv_rows(path: Path, rows: List[Dict[str, str]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(fieldnames))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


# -----------------------------
# Splitting
# -----------------------------
def split_rows(
    rows: List[Dict[str, str]],
    ratios: Tuple[float, float, float],
    seed: int,
) -> Dict[str, List[Dict[str, str]]]:
    train_r, val_r, test_r = ratios
    if abs((train_r + val_r + test_r) - 1.0) > 1e-6:
        raise ValueError(f"Split ratios must sum to 1.0. Got {ratios}")

    rng = random.Random(seed)
    idx = list(range(len(rows)))
    rng.shuffle(idx)

    n = len(rows)
    n_train = int(n * train_r)
    n_val = int(n * val_r)
    n_test = n - n_train - n_val

    train_idx = idx[:n_train]
    val_idx = idx[n_train:n_train + n_val]
    test_idx = idx[n_train + n_val:]

    return {
        "train": [rows[i] for i in train_idx],
        "val": [rows[i] for i in val_idx],
        "test": [rows[i] for i in test_idx],
    }


def validate_tiles_manifest(rows: List[Dict[str, str]]) -> None:
    if not rows:
        raise ValueError("Tiles manifest is empty. Did preprocess produce any rows?")

    # Require tile_path for actual training
    if "tile_path" not in rows[0]:
        raise ValueError("Tiles manifest must include a 'tile_path' column.")

    nonempty = sum(1 for r in rows if (r.get("tile_path") or "").strip())
    if nonempty == 0:
        raise ValueError(
            "Tiles manifest has no tile_path values. "
            "Your preprocess stage likely ran in stub mode and did not write tiles yet."
        )


# -----------------------------
# Optional: placeholder "training"
# -----------------------------
def dummy_train_summary(splits: Dict[str, List[Dict[str, str]]]) -> Dict[str, object]:
    """Produces a JSON-able summary in lieu of real model training."""
    return {
        "status": "no_training_backend_configured",
        "counts": {k: len(v) for k, v in splits.items()},
        "note": "Wire in src/train when your tiler produces real tiles + labels.",
    }


# -----------------------------
# Main
# -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train stage aligned with manifest-driven ingest/preprocess."
    )

    parser.add_argument(
        "--tiles-manifest",
        default="data/interim/tiles/H_glaber_tiles_manifest.csv",
        help="CSV manifest produced by preprocess (tile_path required).",
    )
    parser.add_argument(
        "--splits-outdir",
        default="data/processed",
        help="Where to write train/val/test split manifests.",
    )
    parser.add_argument(
        "--models-outdir",
        default="outputs/models",
        help="Where to write model artifacts per run.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting.")
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)

    # Optional label wiring
    parser.add_argument(
        "--label-column",
        default="label",
        help="Column name containing class label (if present).",
    )
    parser.add_argument(
        "--require-labels",
        action="store_true",
        help="If set, fail if label column is missing/empty.",
    )

    # Logging
    parser.add_argument(
        "--log",
        default=f"outputs/logs/train_{now_stamp()}.log",
        help="Log file path.",
    )

    args = parser.parse_args()

    log = make_logger(Path(args.log))

    tiles_manifest = Path(args.tiles_manifest)
    splits_outdir = Path(args.splits_outdir)
    models_outdir = Path(args.models_outdir)

    log("=" * 60)
    log("TRAIN STAGE")
    log(f"tiles_manifest: {tiles_manifest}")
    log(f"splits_outdir:  {splits_outdir}")
    log(f"models_outdir:  {models_outdir}")
    log(f"seed: {args.seed}")
    log(f"ratios: train={args.train_ratio}, val={args.val_ratio}, test={args.test_ratio}")

    # Load tiles manifest
    rows = read_csv_rows(tiles_manifest)
    log(f"tiles manifest rows: {len(rows)}")

    # Validate
    validate_tiles_manifest(rows)

    # Optional: labels check
    if args.require_labels:
        if args.label_column not in rows[0]:
            raise ValueError(f"Label column '{args.label_column}' not found in tiles manifest.")
        labeled = sum(1 for r in rows if (r.get(args.label_column) or "").strip() != "")
        if labeled == 0:
            raise ValueError(
                f"Label column '{args.label_column}' is present but empty for all rows."
            )
        log(f"labeled rows: {labeled}/{len(rows)}")

    # Split
    splits = split_rows(
        rows,
        ratios=(args.train_ratio, args.val_ratio, args.test_ratio),
        seed=args.seed,
    )
    log(f"split counts: " + ", ".join(f"{k}={len(v)}" for k, v in splits.items()))

    # Write split manifests
    # Keep fieldnames stable: use original columns + add split name
    fieldnames = list(rows[0].keys())
    if "split" not in fieldnames:
        fieldnames = fieldnames + ["split"]

    for split_name, split_rows_list in splits.items():
        for r in split_rows_list:
            r["split"] = split_name

        out_path = splits_outdir / f"{split_name}_tiles_manifest.csv"
        write_csv_rows(out_path, split_rows_list, fieldnames=fieldnames)
        log(f"wrote split manifest: {out_path}")

    # Create run dir for artifacts
    run_name = f"run_{now_stamp()}"
    run_dir = models_outdir / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save run metadata
    meta = {
        "run_name": run_name,
        "tiles_manifest": str(tiles_manifest),
        "splits": {k: len(v) for k, v in splits.items()},
        "seed": args.seed,
        "ratios": {"train": args.train_ratio, "val": args.val_ratio, "test": args.test_ratio},
        "label_column": args.label_column,
        "require_labels": args.require_labels,
        "note": "This entrypoint is aligned to manifest-driven ingest/preprocess. "
                "Wire in src/train to perform actual model training.",
    }
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"wrote run metadata: {run_dir / 'run_meta.json'}")

    # Placeholder training artifact (until src/train is implemented)
    summary = dummy_train_summary(splits)
    (run_dir / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"wrote training summary: {run_dir / 'training_summary.json'}")

    log("TRAIN STAGE COMPLETE")
    log("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
