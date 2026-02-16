"""YAML config loading with validation."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import yaml

def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as fp:
        cfg = yaml.safe_load(fp)
    if cfg is None:
        raise ValueError(f"Config is empty: {path}")
    return cfg


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (override wins)."""
    merged = base.copy()
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged
