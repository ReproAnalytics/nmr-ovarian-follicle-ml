#!/usr/bin/env python3
"""Post-processing: aggregate tile predictions into slide-level follicle counts."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.paths import find_repo_root
from src.utils.io import read_csv_rows, write_csv_rows
from src.utils.logging import make_logger, now_stamp


def main() -> int:
    parser = argparse.ArgumentParser(description="Count follicles per slide from tile predictions.")
    parser.add_argument("--predictions", default="outputs/predictions/tiles_predictions.csv")
    parser.add_argument("--output", default="outputs/predictions/slide_level_predictions.csv")
    args = parser.parse_args()

    repo = find_repo_root(Path.cwd())
    log = make_logger(repo / f"outputs/logs/postprocess_{now_stamp()}.log")

    predictions_csv = repo / args.predictions
    output_csv = repo / args.output

    log("POSTPROCESS (COUNT) STAGE", prefix="postprocess")

    rows = read_csv_rows(predictions_csv)
    log(f"Loaded {len(rows)} tile predictions", prefix="postprocess")

    # Group by slide and count predicted labels
    slide_counts: dict = {}
    for r in rows:
        slide = r.get("slide_path", "unknown")
        label = r.get("predicted_label", "unlabeled")
        if slide not in slide_counts:
            slide_counts[slide] = Counter()
        slide_counts[slide][label] += 1

    out_rows = []
    for slide, counts in sorted(slide_counts.items()):
        out_rows.append({
            "slide_path": slide,
            "total_tiles": str(sum(counts.values())),
            **{f"count_{k}": str(v) for k, v in sorted(counts.items())},
        })

    if out_rows:
        fieldnames = list(out_rows[0].keys())
        write_csv_rows(output_csv, out_rows, fieldnames)
        log(f"Wrote slide-level counts: {output_csv}", prefix="postprocess")
    else:
        log("WARNING: no predictions to aggregate", prefix="postprocess")

    log("POSTPROCESS STAGE COMPLETE", prefix="postprocess")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())