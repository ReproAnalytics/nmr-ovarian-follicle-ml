#!/usr/bin/env python3
"""
Evaluation stage: compute per-class precision/recall/F1 + macro averages.

Input:
- outputs/predictions/tiles_predictions.csv with columns:
  tile_path,true_label,predicted_label,confidence

Output:
- outputs/metrics/tiles_metrics.json
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List

from sklearn.metrics import classification_report, confusion_matrix

# repo-local
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.config import load_config


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        return [dict(r) for r in reader]


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate tile predictions.")
    ap.add_argument("--config", default="configs/eval.yaml")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    cfg = load_config(repo / args.config)

    preds_csv = repo / cfg["paths"]["predictions_csv"]
    metrics_json = repo / cfg["paths"]["metrics_json"]
    avg = str(cfg["eval"].get("average", "macro"))

    rows = read_csv_rows(preds_csv)
    if not rows:
        raise ValueError("Predictions CSV is empty.")

    required = {"true_label", "predicted_label"}
    if not required.issubset(rows[0].keys()):
        raise ValueError(f"Predictions CSV must contain columns {sorted(required)}")

    y_true = []
    y_pred = []
    for r in rows:
        tl = (r.get("true_label") or "").strip()
        pl = (r.get("predicted_label") or "").strip()
        if not tl:
            continue
        if not pl:
            continue
        y_true.append(tl)
        y_pred.append(pl)

    if not y_true:
        raise ValueError(
            "No rows with non-empty true_label found. "
            "You need labels in the tiles manifest (or a joined gold-set) before eval."
        )

    labels = sorted(set(y_true) | set(y_pred))
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    out = {
        "n_evaluated": len(y_true),
        "labels": labels,
        "classification_report": report,
        "confusion_matrix": {
            "labels": labels,
            "matrix": cm.tolist(),
        },
        "average": avg,
    }

    metrics_json.parent.mkdir(parents=True, exist_ok=True)
    metrics_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[eval] wrote metrics to {metrics_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
