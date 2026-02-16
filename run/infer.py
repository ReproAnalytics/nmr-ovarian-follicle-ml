#!/usr/bin/env python3
"""
Inference stage: run trained model on tiles and write predictions CSV.

Inputs:
- configs/infer.yaml
- tiles manifest CSV with column tile_path (and optionally label)
- model checkpoint (default outputs/models/latest.pt)

Output:
- outputs/predictions/tiles_predictions.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional

import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image

import torchvision
from torchvision import transforms

# repo-local
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.config import load_config


def pick_device(device_cfg: str) -> torch.device:
    dc = (device_cfg or "auto").lower()
    if dc == "cpu":
        return torch.device("cpu")
    if dc == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if dc == "mps":
        return torch.device("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")

    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


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


class TileOnlyDataset(Dataset):
    def __init__(self, rows: List[Dict[str, str]], tile_col: str, label_col: Optional[str], transform):
        self.rows = rows
        self.tile_col = tile_col
        self.label_col = label_col
        self.transform = transform

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        r = self.rows[idx]
        tile_path = (r.get(self.tile_col) or "").strip()
        if not tile_path:
            raise ValueError(f"Empty tile_path at row {idx}")
        p = Path(tile_path)
        if not p.exists():
            raise FileNotFoundError(f"Tile image not found: {p}")

        img = Image.open(p).convert("RGB")
        x = self.transform(img)
        true_label = (r.get(self.label_col) or "").strip() if self.label_col else ""
        return tile_path, true_label, x


def build_transforms(image_size: int):
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])


def build_model(backbone: str, num_classes: int) -> torch.nn.Module:
    bb = (backbone or "resnet18").lower()
    if bb != "resnet18":
        raise ValueError(f"Only 'resnet18' is implemented right now, got '{backbone}'")

    model = torchvision.models.resnet18(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    return model


@torch.no_grad()
def main() -> int:
    ap = argparse.ArgumentParser(description="Run inference on tiles.")
    ap.add_argument("--config", default="configs/infer.yaml")
    ap.add_argument("--tile-col", default="tile_path")
    ap.add_argument("--label-col", default="label")  # optional in manifest
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    cfg = load_config(repo / args.config)

    tiles_manifest = repo / cfg["paths"]["tiles_manifest"]
    ckpt_path = repo / cfg["paths"]["checkpoint_path"]
    preds_csv = repo / cfg["paths"]["predictions_csv"]

    icfg = cfg["infer"]
    batch_size = int(icfg["batch_size"])
    num_workers = int(icfg["num_workers"])
    image_size = int(icfg["image_size"])
    device = pick_device(str(icfg.get("device", "auto")))

    rows = read_csv_rows(tiles_manifest)
    if not rows:
        raise ValueError("Tiles manifest is empty.")

    # Filter to rows with real tile paths
    usable = []
    for r in rows:
        tile = (r.get(args.tile_col) or "").strip()
        if tile and Path(tile).exists():
            usable.append(r)
    if not usable:
        raise ValueError("No usable tiles (existing tile files) found for inference.")

    ckpt = torch.load(ckpt_path, map_location="cpu")
    label_to_id = ckpt["label_to_id"]
    id_to_label = ckpt["id_to_label"]
    backbone = ckpt.get("backbone", "resnet18")
    image_size = int(ckpt.get("image_size", image_size))

    model = build_model(backbone, num_classes=len(label_to_id))
    model.load_state_dict(ckpt["model_state"])
    model.to(device)
    model.eval()

    transform = build_transforms(image_size)
    ds = TileOnlyDataset(usable, args.tile_col, args.label_col, transform)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=(device.type != "cpu"))

    out_rows: List[Dict[str, str]] = []
    softmax = torch.nn.Softmax(dim=1)

    for tile_paths, true_labels, x in loader:
        x = x.to(device, non_blocking=True)
        logits = model(x)
        probs = softmax(logits)
        conf, pred = torch.max(probs, dim=1)

        for tp, tl, c, p in zip(tile_paths, true_labels, conf.cpu().tolist(), pred.cpu().tolist()):
            out_rows.append({
                "tile_path": str(tp),
                "true_label": str(tl),
                "predicted_label": str(id_to_label[int(p)]),
                "confidence": f"{float(c):.6f}",
            })

    write_csv_rows(preds_csv, out_rows, ["tile_path", "true_label", "predicted_label", "confidence"])
    print(f"[infer] wrote {len(out_rows)} predictions to {preds_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
