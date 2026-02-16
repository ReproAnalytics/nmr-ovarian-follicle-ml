#!/usr/bin/env python3
"""Inference stage: load trained model and predict on tiles."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.paths import find_repo_root
from src.utils.config import load_config
from src.utils.io import read_csv_rows, write_csv_rows
from src.utils.logging import make_logger, now_stamp


def main() -> int:
    parser = argparse.ArgumentParser(description="Run inference on tile images.")
    parser.add_argument("--config", default="configs/infer.yaml")
    args = parser.parse_args()

    repo = find_repo_root(Path.cwd())
    cfg = load_config(repo / args.config)

    log = make_logger(repo / f"outputs/logs/infer_{now_stamp()}.log")
    log("INFERENCE STAGE", prefix="infer")
    log(f"config: {args.config}", prefix="infer")

    tiles_manifest = repo / cfg["paths"]["tiles_manifest"]
    checkpoint = repo / cfg["paths"]["checkpoint_path"]
    predictions_csv = repo / cfg["paths"]["predictions_csv"]

    if not checkpoint.exists():
        log(f"ERROR: checkpoint not found: {checkpoint}", prefix="infer")
        log("Train a model first (python run/train.py)", prefix="infer")
        return 1

    rows = read_csv_rows(tiles_manifest)
    log(f"Loaded {len(rows)} tiles", prefix="infer")

    # TODO: Load model from checkpoint, run forward pass on each tile batch,
    #       append predicted class and confidence to each row.
    log("WARNING: inference logic not yet implemented — writing stub predictions", prefix="infer")

    for r in rows:
        r["predicted_label"] = ""
        r["confidence"] = ""

    fieldnames = list(rows[0].keys()) if rows else []
    write_csv_rows(predictions_csv, rows, fieldnames)
    log(f"Wrote predictions: {predictions_csv}", prefix="infer")
    log("INFERENCE STAGE COMPLETE", prefix="infer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())