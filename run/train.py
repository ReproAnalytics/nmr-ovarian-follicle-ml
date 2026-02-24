#!/usr/bin/env python3
"""
Train a tile-level follicle classifier (torchvision resnet18).

Expected inputs:
- configs/train.yaml
- tiles manifest CSV with columns: tile_path, label
- annotations/labelmap.json where keys match label values in tiles manifest

Outputs:
- data/processed/{train,val,test}_manifest.csv
- outputs/models/<run_name>/model.pt
- outputs/models/latest.pt
- outputs/logs/train_<run_name>.log

Debugging and code assistance for image analysis and model training were provided by ChatGPT (GPT 5.2 Thinking)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from PIL import Image

import torchvision
from torchvision import transforms

# repo-local
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.config import load_config


# -----------------------------
# Utilities
# -----------------------------
def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def pick_device(device_cfg: str) -> torch.device:
    dc = (device_cfg or "auto").lower()
    if dc == "cpu":
        return torch.device("cpu")
    if dc == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if dc == "mps":
        return torch.device("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")

    # auto
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def make_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        line = f"[train] {msg}"
        print(line)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")

    return log


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        return [dict(r) for r in reader]


def write_csv_rows(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def split_rows(
    rows: List[Dict[str, str]],
    ratios: Tuple[float, float, float],
    seed: int,
) -> Dict[str, List[Dict[str, str]]]:
    tr, vr, te = ratios
    if abs((tr + vr + te) - 1.0) > 1e-6:
        raise ValueError(f"Split ratios must sum to 1.0, got {ratios}")

    rng = random.Random(seed)
    idx = list(range(len(rows)))
    rng.shuffle(idx)

    n = len(rows)
    n_train = int(n * tr)
    n_val = int(n * vr)
    train_idx = idx[:n_train]
    val_idx = idx[n_train:n_train + n_val]
    test_idx = idx[n_train + n_val:]

    return {
        "train": [rows[i] for i in train_idx],
        "val": [rows[i] for i in val_idx],
        "test": [rows[i] for i in test_idx],
    }


def validate_rows(rows: List[Dict[str, str]], tile_col: str, label_col: str) -> None:
    if not rows:
        raise ValueError("Tiles manifest is empty.")

    if tile_col not in rows[0]:
        raise ValueError(f"Tiles manifest missing required column '{tile_col}'")
    if label_col not in rows[0]:
        raise ValueError(f"Tiles manifest missing required column '{label_col}'")

    nonempty_tiles = sum(1 for r in rows if (r.get(tile_col) or "").strip())
    if nonempty_tiles == 0:
        raise ValueError(
            f"No non-empty '{tile_col}' values found. "
            f"Preprocess is likely still in stub mode (no tiles written)."
        )


# -----------------------------
# Dataset
# -----------------------------
class TileDataset(Dataset):
    def __init__(
        self,
        rows: List[Dict[str, str]],
        tile_col: str,
        label_col: str,
        label_to_id: Dict[str, int],
        transform,
    ):
        self.rows = rows
        self.tile_col = tile_col
        self.label_col = label_col
        self.label_to_id = label_to_id
        self.transform = transform

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        r = self.rows[idx]
        tile_path = (r.get(self.tile_col) or "").strip()
        label = (r.get(self.label_col) or "").strip()

        if not tile_path:
            raise ValueError(f"Empty tile_path at row {idx}")
        if label not in self.label_to_id:
            raise ValueError(f"Unknown label '{label}' at row {idx}")

        p = Path(tile_path)
        if not p.exists():
            raise FileNotFoundError(f"Tile image not found: {p}")

        img = Image.open(p).convert("RGB")
        img = self.transform(img)
        y = self.label_to_id[label]
        return img, y


def build_transforms(image_size: int):
    # Standard ImageNet normalization (works well for resnet backbones)
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])


def build_model(backbone: str, num_classes: int) -> nn.Module:
    bb = (backbone or "resnet18").lower()
    if bb != "resnet18":
        raise ValueError(f"Only 'resnet18' is implemented right now, got '{backbone}'")

    model = torchvision.models.resnet18(weights=None)  # avoid internet downloads
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


# -----------------------------
# Train loop
# -----------------------------
def train_one_epoch(model, loader, optimizer, loss_fn, device) -> float:
    model.train()
    total_loss = 0.0
    n = 0
    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = loss_fn(logits, y)
        loss.backward()
        optimizer.step()

        bs = x.shape[0]
        total_loss += loss.item() * bs
        n += bs
    return total_loss / max(n, 1)


@torch.no_grad()
def eval_one_epoch(model, loader, loss_fn, device) -> Tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    n = 0
    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        logits = model(x)
        loss = loss_fn(logits, y)

        preds = torch.argmax(logits, dim=1)
        correct += (preds == y).sum().item()

        bs = x.shape[0]
        total_loss += loss.item() * bs
        n += bs

    avg_loss = total_loss / max(n, 1)
    acc = correct / max(n, 1)
    return avg_loss, acc


def main() -> int:
    ap = argparse.ArgumentParser(description="Train follicle tile classifier.")
    ap.add_argument("--config", default="configs/train.yaml", help="Path to train config YAML.")
    ap.add_argument("--tile-col", default="tile_path", help="Column name for tile image path.")
    ap.add_argument("--label-col", default="label", help="Column name for class label.")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    cfg = load_config(repo / args.config)

    # Paths
    tiles_manifest = repo / cfg["paths"]["tiles_manifest"]
    labelmap_path = repo / cfg["paths"]["labelmap"]

    output_dir = repo / cfg["paths"].get("output_dir", "outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    run_name = cfg["paths"].get("run_name") or f"run_{now_stamp()}"
    models_dir = output_dir / "models" / run_name
    models_dir.mkdir(parents=True, exist_ok=True)

    latest_ckpt = output_dir / "models" / "latest.pt"
    log_path = output_dir / "logs" / f"train_{run_name}.log"
    log = make_logger(log_path)

    # Load labelmap (keys are labels)
    labelmap = json.loads(labelmap_path.read_text(encoding="utf-8"))
    label_to_id = {k: int(v) for k, v in labelmap.items()}
    id_to_label = {int(v): k for k, v in labelmap.items()}

    # Load manifest
    rows = read_csv_rows(tiles_manifest)
    log(f"tiles_manifest: {tiles_manifest}")
    log(f"rows: {len(rows)}")

    validate_rows(rows, args.tile_col, args.label_col)

    # Filter to rows with valid labels + existing tiles
    filtered = []
    missing_tiles = 0
    bad_labels = 0
    for r in rows:
        tile = (r.get(args.tile_col) or "").strip()
        lab = (r.get(args.label_col) or "").strip()
        if not tile:
            continue
        if lab not in label_to_id:
            bad_labels += 1
            continue
        if not Path(tile).exists():
            missing_tiles += 1
            continue
        filtered.append(r)

    if not filtered:
        raise ValueError("After filtering, no usable (tile_path,label) rows remain.")

    if bad_labels:
        log(f"WARNING: dropped {bad_labels} rows with labels not in labelmap.json")
    if missing_tiles:
        log(f"WARNING: dropped {missing_tiles} rows whose tile files do not exist")

    # Split
    seed = int(cfg["data"]["split"]["seed"])
    ratios = (
        float(cfg["data"]["split"]["train"]),
        float(cfg["data"]["split"]["val"]),
        float(cfg["data"]["split"]["test"]),
    )
    splits = split_rows(filtered, ratios, seed)
    log(f"splits: train={len(splits['train'])}, val={len(splits['val'])}, test={len(splits['test'])}")

    # Write split manifests
    processed_dir = repo / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted(set().union(*(r.keys() for r in filtered)))
    write_csv_rows(processed_dir / "train_manifest.csv", splits["train"], fieldnames)
    write_csv_rows(processed_dir / "val_manifest.csv", splits["val"], fieldnames)
    write_csv_rows(processed_dir / "test_manifest.csv", splits["test"], fieldnames)
    log(f"wrote split manifests to {processed_dir}")

    # Training cfg
    tcfg = cfg["train"]
    epochs = int(tcfg["epochs"])
    batch_size = int(tcfg["batch_size"])
    lr = float(tcfg["lr"])
    wd = float(tcfg["weight_decay"])
    num_workers = int(tcfg["num_workers"])
    image_size = int(tcfg["image_size"])
    backbone = str(tcfg["backbone"])
    device = pick_device(str(tcfg.get("device", "auto")))

    log(f"device: {device}")
    log(f"backbone: {backbone} | image_size={image_size} | epochs={epochs} | bs={batch_size} | lr={lr} | wd={wd}")

    transform = build_transforms(image_size)

    train_ds = TileDataset(splits["train"], args.tile_col, args.label_col, label_to_id, transform)
    val_ds = TileDataset(splits["val"], args.tile_col, args.label_col, label_to_id, transform)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=(device.type != "cpu"))
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=(device.type != "cpu"))

    model = build_model(backbone, num_classes=len(label_to_id)).to(device)

    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)

    best_val_loss = float("inf")
    best_path = models_dir / "model.pt"

    for epoch in range(1, epochs + 1):
        tr_loss = train_one_epoch(model, train_loader, optimizer, loss_fn, device)
        va_loss, va_acc = eval_one_epoch(model, val_loader, loss_fn, device)

        log(f"epoch {epoch}/{epochs} | train_loss={tr_loss:.4f} | val_loss={va_loss:.4f} | val_acc={va_acc:.4f}")

        # Save best
        if va_loss < best_val_loss:
            best_val_loss = va_loss
            ckpt = {
                "run_name": run_name,
                "backbone": backbone,
                "image_size": image_size,
                "label_to_id": label_to_id,
                "id_to_label": id_to_label,
                "model_state": model.state_dict(),
            }
            torch.save(ckpt, best_path)
            torch.save(ckpt, latest_ckpt)
            log(f"saved best checkpoint: {best_path} (and updated latest.pt)")

    log("training complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
