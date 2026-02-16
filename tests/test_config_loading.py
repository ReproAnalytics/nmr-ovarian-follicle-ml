"""Smoke tests for config loading and path resolution."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.config import load_config
from src.utils.paths import find_repo_root


def test_repo_root_is_found():
    root = find_repo_root()
    assert (root / "configs").is_dir()
    assert (root / "src").is_dir()


@pytest.mark.parametrize("cfg_name", [
    "dataset.yaml",
    "preprocess.yaml",
    "train.yaml",
    "infer.yaml",
    "eval.yaml",
])
def test_config_loads(cfg_name):
    root = find_repo_root()
    cfg = load_config(root / "configs" / cfg_name)
    assert isinstance(cfg, dict)
    assert len(cfg) > 0


def test_dataset_config_has_paths():
    root = find_repo_root()
    cfg = load_config(root / "configs" / "dataset.yaml")
    assert "paths" in cfg
    assert "raw_root" in cfg["paths"]


def test_train_config_splits_sum_to_one():
    root = find_repo_root()
    cfg = load_config(root / "configs" / "train.yaml")
    split = cfg["data"]["split"]
    total = split["train"] + split["val"] + split["test"]
    assert abs(total - 1.0) < 1e-6, f"Split ratios sum to {total}, expected 1.0"