"""Repo root resolution — single source of truth."""
from pathlib import Path

_MARKERS = ("configs", "src", "environment", ".git", "README.md")

def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for _ in range(20):
        if any((cur / m).exists() for m in _MARKERS):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError("Could not locate repo root.")
