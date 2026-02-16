"""Structured file-backed logging."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def make_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg: str, prefix: str = "pipeline") -> None:
        line = f"[{prefix}] {msg}"
        print(line)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")

    return log