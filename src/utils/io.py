"""Shared CSV manifest I/O utilities."""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Dict, List, Sequence


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    with path.open("r", newline="", encoding="utf-8") as fp:
        return [dict(r) for r in csv.DictReader(fp)]


def write_csv_rows(
    path: Path,
    rows: List[Dict[str, str]],
    fieldnames: Sequence[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and fieldnames is None:
        raise ValueError("Cannot write CSV: no rows and no fieldnames provided.")
    fnames = list(fieldnames) if fieldnames else list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fnames})
