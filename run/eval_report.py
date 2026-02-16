#!/usr/bin/env python3
"""Evaluation stage: compute metrics from predictions vs ground truth."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.paths import find_repo_root
from src.utils.config import load_config
from src.utils.io import read_csv_rows
from src.utils.logging import make_logger, now_stamp


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate predictions and generate report.")
    parser.add_argument("--config", default="configs/eval.yaml")
    args = parser.parse_args()

    repo = find_repo_root(Path.cwd())
    cfg = load_config(repo / args.config)
    log = make_logger(repo / f"outputs/logs/eval_{now_stamp()}.log")

    log("EVAL STAGE", prefix="eval")

    predictions_csv = repo / cfg["paths"]["predictions_csv"]
    metrics_json = repo / cfg["paths"]["metrics_json"]

    if not predictions_csv.exists():
        log(f"ERROR: predictions not found: {predictions_csv}", prefix="eval")
        return 1

    rows = read_csv_rows(predictions_csv)
    log(f"Loaded {len(rows)} prediction rows", prefix="eval")

    # TODO: Compare predicted_label to ground-truth label column,
    #       compute precision/recall/F1 via sklearn, write metrics JSON.
    log("WARNING: evaluation logic not yet implemented — writing stub metrics", prefix="eval")

    metrics = {
        "status": "stub",
        "n_predictions": len(rows),
        "average": cfg.get("eval", {}).get("average", "macro"),
        "note": "Implement with sklearn.metrics when labels are available.",
    }

    metrics_json.parent.mkdir(parents=True, exist_ok=True)
    metrics_json.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log(f"Wrote metrics: {metrics_json}", prefix="eval")

    log("EVAL STAGE COMPLETE", prefix="eval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())