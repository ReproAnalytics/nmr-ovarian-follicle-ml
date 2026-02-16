#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.config import load_config
from src.utils.paths import find_repo_root


def _pick_col(cols: list[str], candidates: list[str]) -> str:
    lower = {c.lower(): c for c in cols}
    for k in candidates:
        if k.lower() in lower:
            return lower[k.lower()]
    raise ValueError(f"Could not find any of columns {candidates} in {cols}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return list(r)


def main() -> int:
    ap = argparse.ArgumentParser(description="Join QuPath exports into labeled tiles CSV.")
    ap.add_argument("--config", default="configs/annotate.yaml")
    args = ap.parse_args()

    repo = find_repo_root()
    cfg = load_config(repo / args.config)

    raw_exports = repo / cfg["paths"]["raw_exports"]
    labelmap_path = repo / cfg["paths"]["labelmap"]
    gold_out = repo / cfg["paths"]["gold_set"]

    labelmap = json.loads(labelmap_path.read_text(encoding="utf-8"))
    valid_labels = set(labelmap.keys())

    csv_files = sorted(raw_exports.glob("*.csv"))
    if not csv_files:
        raise SystemExit(f"No CSV exports found in {raw_exports}")

    # votes[tile_path] = [label1, label2, ...]
    votes: dict[str, list[str]] = defaultdict(list)

    for f in csv_files:
        rows = read_rows(f)
        if not rows:
            continue
        cols = list(rows[0].keys())
        tile_col = _pick_col(cols, ["tile_path", "tile", "path", "image"])
        label_col = _pick_col(cols, ["label", "classification", "class"])

        for r in rows:
            tile = (r.get(tile_col) or "").strip()
            lab = (r.get(label_col) or "").strip()
            if not tile or not lab:
                continue
            if lab not in valid_labels:
                # ignore unknown labels but keep going
                continue
            votes[tile].append(lab)

    strategy = cfg.get("annotate", {}).get("strategy", "majority_vote")
    min_agreement = int(cfg.get("annotate", {}).get("min_agreement", 1))

    out_rows: list[dict[str, str]] = []
    for tile, labs in sorted(votes.items()):
        c = Counter(labs)
        best, n = c.most_common(1)[0]
        if strategy == "majority_vote" and n < min_agreement:
            continue
        out_rows.append({"tile_path": tile, "label": best})

    gold_out.parent.mkdir(parents=True, exist_ok=True)
    with gold_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tile_path", "label"])
        w.writeheader()
        w.writerows(out_rows)

    print(f"[annotate] wrote {len(out_rows)} labeled tiles to {gold_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
