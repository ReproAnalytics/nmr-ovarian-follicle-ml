#!/usr/bin/env python3
"""
Ovarian Follicle Classification Pipeline
-----------------------------------------
ResNet34 transfer-learning classifier for histological tile images,
with whole-slide image (WSI) inference support. 

Expected directory layout:
    <data_dir>/
        train/          ← one subfolder per class (e.g. Primordial/, Stroma/)
        valid/          ← same class subfolders
        test/           ← same class subfolders

Usage:
    python cnn_pipeline.py --config configs/train.yaml

Debugging and code assistance for image analysis and model training
were provided by ChatGPT (GPT 5.2 Thinking) and Claude (Opus 4.6).
"""

from __future__ import annotations

import argparse
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
import tifffile
from PIL import Image

from fastai.vision.all import (
    ImageDataLoaders, Resize, Normalize, imagenet_stats,
    cnn_learner, resnet34, error_rate, ClassificationInterpretation,
    aug_transforms, CrossEntropyLossFlat,
)
from fastai.callback.tracker import EarlyStoppingCallback, SaveModelCallback
from sklearn.metrics import roc_curve, auc

# repo-local config loader
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.config import load_config


# ======================================================================
# Utilities
# ======================================================================

def now_stamp() -> str:
    """Compact timestamp for run naming."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def pick_device(device_cfg: str) -> torch.device:
    """Resolve 'auto' / 'cuda' / 'mps' / 'cpu' to a torch.device."""
    dc = (device_cfg or "auto").lower()
    if dc == "cpu":
        return torch.device("cpu")
    if dc == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if dc == "mps":
        has_mps = getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
        return torch.device("mps" if has_mps else "cpu")
    # auto
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def make_logger(log_path: Path):
    """Return a simple log(msg) function that prints + appends to file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        line = f"[pipeline] {msg}"
        print(line)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")

    return log


# ======================================================================
# Class-weight computation
# ======================================================================

def compute_class_weights(data_dir: Path, vocab: list, device: torch.device) -> torch.Tensor:
    """
    Compute inverse-frequency class weights from the training folder layout.

    For each class in vocab, counts the number of image files in
    data_dir/train/<class_name>/, then returns normalized weights
    so that rare classes receive higher loss contribution.
    """
    image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    counts = []
    for class_name in vocab:
        class_dir = data_dir / "train" / class_name
        if class_dir.exists():
            n = sum(1 for f in class_dir.iterdir() if f.suffix.lower() in image_exts)
        else:
            n = 0
        counts.append(max(n, 1))  # avoid division by zero

    counts_arr = np.array(counts, dtype=np.float64)
    weights = 1.0 / counts_arr
    weights = weights / weights.sum() * len(weights)  # normalize so weights sum to num_classes

    return torch.FloatTensor(weights).to(device)


# ======================================================================
# Tissue detection & WSI tiling (tifffile + PIL)
# ======================================================================

def is_tissue(tile_arr: np.ndarray, threshold: int = 220) -> bool:
    """Simple mean-intensity background filter on a numpy RGB array."""
    return float(np.mean(tile_arr)) < threshold


def read_slide_array(slide_path: Path, level: int = 0) -> np.ndarray:
    """
    Read a TIFF slide into a numpy RGB array using tifffile.

    Handles three cases:
      1. Pyramid TIFF with multiple resolution levels in series[0]
      2. Multi-page TIFF where each page is a resolution level
      3. Plain single-page TIFF (level 0 only; higher levels are
         produced by downsampling by 2^level)

    Returns an (H, W, 3) uint8 RGB array.
    """
    needs_downsample = False

    with tifffile.TiffFile(str(slide_path)) as tf:
        # --- Case 1: pyramid levels in the first series ---
        if tf.series:
            series = tf.series[0]
            n_levels = len(series.levels) if hasattr(series, "levels") else 1

            if n_levels > 1 and level < n_levels:
                img = series.levels[level].asarray()
            elif n_levels > 1:
                # requested level exceeds available — use coarsest
                print(f"  level {level} unavailable ({n_levels} levels), using level {n_levels - 1}")
                img = series.levels[n_levels - 1].asarray()
            else:
                # single-level series — flag for downsampling
                img = series.asarray()
                if level > 0:
                    needs_downsample = True
        # --- Case 2: multi-page ---
        elif len(tf.pages) > 1 and level < len(tf.pages):
            img = tf.pages[level].asarray()
        # --- Case 3: plain single-page ---
        else:
            img = tf.pages[0].asarray()
            if level > 0:
                needs_downsample = True

    # Downsample if we only got the full-resolution page
    if needs_downsample:
        factor = 2 ** level
        img = img[::factor, ::factor]
        print(f"  plain TIFF — downsampled by {factor}x for level {level}")

    # Ensure 3-channel RGB
    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    elif img.ndim == 3 and img.shape[2] == 4:
        img = img[:, :, :3]  # drop alpha

    return img.astype(np.uint8)


def tile_wsi(slide_arr: np.ndarray, tile_size: int = 224, stride: int = 224):
    """
    Extract tissue-containing tiles from a slide numpy array.

    Args:
        slide_arr: (H, W, 3) uint8 RGB array
        tile_size: tile width/height in pixels
        stride: step between tiles

    Returns:
        tiles: list of PIL.Image.Image (RGB)
        coords: list of (x, y) tuples (pixel coords at this resolution)
    """
    height, width = slide_arr.shape[:2]
    tiles = []
    coords = []

    for y in range(0, height - tile_size + 1, stride):
        for x in range(0, width - tile_size + 1, stride):
            patch = slide_arr[y : y + tile_size, x : x + tile_size]
            if is_tissue(patch):
                tiles.append(Image.fromarray(patch))
                coords.append((x, y))

    return tiles, coords


# ======================================================================
# WSI-level inference
# ======================================================================

def analyze_wsi(slide_path: Path, learn, level: int = 1):
    """
    Run trained model over every tissue tile in a WSI.

    Uses tifffile to read MOTHER plain TIFFs (which OpenSlide cannot open).
    """
    print(f"\nProcessing: {slide_path}")
    try:
        slide_arr = read_slide_array(slide_path, level=level)
    except Exception as exc:
        print(f"  ERROR reading {slide_path.name}: {exc}")
        return None

    h, w = slide_arr.shape[:2]
    print(f"  slide array shape: {w}x{h} (level {level})")

    tiles, coords = tile_wsi(slide_arr, tile_size=224, stride=224)
    # Free the full-resolution array to reclaim memory
    del slide_arr

    if len(tiles) == 0:
        print("  No tissue detected.")
        return None

    print(f"  tissue tiles extracted: {len(tiles)}")

    dl = learn.dls.test_dl(tiles)
    preds, _ = learn.get_preds(dl=dl)
    pred_classes = preds.argmax(dim=1)

    counts = {cls: 0 for cls in learn.dls.vocab}
    spatial_results = []

    for i, cls_idx in enumerate(pred_classes):
        label = learn.dls.vocab[cls_idx]
        counts[label] += 1
        x, y = coords[i]
        spatial_results.append({"x": x, "y": y, "prediction": label})

    return counts, spatial_results


# ======================================================================
# Main pipeline
# ======================================================================

def parse_args():
    ap = argparse.ArgumentParser(description="Ovarian follicle CNN pipeline")
    ap.add_argument(
        "--config", default="configs/train.yaml",
        help="Path to YAML config (default: configs/train.yaml)",
    )
    ap.add_argument(
        "--skip-wsi", action="store_true",
        help="Skip the WSI inference stage",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()

    # ----- resolve repo root & load config -----
    repo = Path(__file__).resolve().parent.parent
    cfg = load_config(repo / args.config)

    # ----- paths from config -----
    data_dir = repo / cfg["paths"]["data_dir"]
    test_dir = repo / cfg["paths"].get("test_dir", str(data_dir / "test"))
    output_dir = repo / cfg["paths"].get("output_dir", "outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    run_name = cfg["paths"].get("run_name") or f"run_{now_stamp()}"
    models_dir = output_dir / "models" / run_name
    models_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "logs" / f"pipeline_{run_name}.log"
    log = make_logger(log_path)

    log(f"run_name: {run_name}")
    log(f"config:   {args.config}")
    log(f"data_dir: {data_dir}")

    # ----- training config -----
    tcfg = cfg["train"]
    epochs_head = int(tcfg.get("epochs_head", 5))
    epochs_full = int(tcfg.get("epochs_full", 10))
    batch_size = int(tcfg["batch_size"])
    lr_head = float(tcfg.get("lr_head", 1e-3))
    lr_full_min = float(tcfg.get("lr_full_min", 1e-5))
    lr_full_max = float(tcfg.get("lr_full_max", 1e-3))
    image_size = int(tcfg["image_size"])
    patience = int(tcfg.get("patience", 3))
    device = pick_device(str(tcfg.get("device", "auto")))

    log(f"device: {device}")
    log(
        f"image_size={image_size}  bs={batch_size}  "
        f"epochs_head={epochs_head}  epochs_full={epochs_full}  "
        f"lr_head={lr_head}  lr_full=[{lr_full_min}, {lr_full_max}]  "
        f"patience={patience}"
    )

    # ==================================================================
    # Build fastai DataLoaders with augmentation
    # ==================================================================
    log("building DataLoaders from folder layout (with augmentation)")

    dls = ImageDataLoaders.from_folder(
        data_dir,
        train="train",
        valid="valid",
        item_tfms=Resize(image_size),
        batch_tfms=[
            *aug_transforms(
                flip_vert=True,       # vertical flips are safe for histology (no canonical orientation)
                max_rotate=90.0,      # full 90-degree rotation range
                max_zoom=1.2,         # mild zoom to simulate scale variation
                max_lighting=0.3,     # brightness/contrast jitter for staining variation
                max_warp=0.15,        # slight perspective warping
                p_affine=0.75,        # probability of applying affine transforms
                p_lighting=0.75,      # probability of applying lighting transforms
            ),
            Normalize.from_stats(*imagenet_stats),
        ],
        bs=batch_size,
    )
    log(f"classes: {list(dls.vocab)}")

    # ==================================================================
    # Compute class weights for imbalance correction
    # ==================================================================
    class_weights = compute_class_weights(data_dir, list(dls.vocab), device)
    loss_func = CrossEntropyLossFlat(weight=class_weights)

    # Log per-class training counts and weights
    image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    for i, class_name in enumerate(dls.vocab):
        class_dir = data_dir / "train" / class_name
        n = sum(1 for f in class_dir.iterdir() if f.suffix.lower() in image_exts) if class_dir.exists() else 0
        log(f"  {class_name}: {n} train tiles, weight={class_weights[i]:.4f}")

    # ==================================================================
    # Create learner (pretrained ResNet34) with weighted loss
    # ==================================================================
    log("initialising ResNet34 learner (ImageNet pretrained, weighted CE loss)")
    learn = cnn_learner(dls, resnet34, metrics=error_rate, loss_func=loss_func)
    learn.model.to(device)

    # ==================================================================
    # Phase 1 — frozen fine-tune (head only)
    # ==================================================================
    log(f"phase 1: frozen fine-tune ({epochs_head} epochs, lr={lr_head})")
    learn.fine_tune(
        epochs_head,
        base_lr=lr_head,
        cbs=[
            EarlyStoppingCallback(monitor="valid_loss", patience=patience),
            SaveModelCallback(monitor="valid_loss", fname="best_resnet34"),
        ],
    )

    # ==================================================================
    # Phase 2 — unfrozen full training
    # ==================================================================
    log(f"phase 2: unfrozen training ({epochs_full} epochs, lr=[{lr_full_min}, {lr_full_max}])")
    learn.unfreeze()
    learn.fit_one_cycle(
        epochs_full,
        lr_max=slice(lr_full_min, lr_full_max),
        cbs=[
            EarlyStoppingCallback(monitor="valid_loss", patience=patience),
            SaveModelCallback(monitor="valid_loss", fname="best_resnet34"),
        ],
    )

    # ==================================================================
    # Load best checkpoint
    # ==================================================================
    log("loading best checkpoint")
    learn.load("best_resnet34")
    learn.model.eval()

    # Save a portable copy alongside run outputs
    best_src = learn.path / learn.model_dir / "best_resnet34.pth"
    best_dst = models_dir / "best_resnet34.pth"
    if best_src.exists():
        import shutil
        shutil.copy2(best_src, best_dst)
        log(f"copied best model → {best_dst}")

    # ==================================================================
    # Evaluation — confusion matrix & top losses
    # ==================================================================
    log("generating confusion matrix & top-losses plot")
    interp = ClassificationInterpretation.from_learner(learn)

    interp.plot_confusion_matrix()
    plt.savefig(output_dir / "confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close()

    interp.plot_top_losses(5)
    plt.savefig(output_dir / "top_losses.png", dpi=150, bbox_inches="tight")
    plt.close()
    log(f"saved confusion_matrix.png, top_losses.png → {output_dir}")

    # ==================================================================
    # Evaluation — multi-class ROC curves
    # ==================================================================
    log("generating multi-class ROC curves")
    preds_val, targs_val = learn.get_preds()

    plt.figure(figsize=(10, 8))
    for i, class_name in enumerate(dls.vocab):
        fpr, tpr, _ = roc_curve(
            (targs_val == i).numpy(), preds_val[:, i].numpy(),
        )
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"{class_name} (AUC = {roc_auc:.2f})")

    plt.plot([0, 1], [0, 1], "k--", label="Random Chance (AUC = 0.50)")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate (1 − Specificity)")
    plt.ylabel("True Positive Rate (Sensitivity)")
    plt.title("Multi-Class ROC Curve: Ovarian Follicle Classification")
    plt.legend(loc="lower right")
    plt.grid(alpha=0.3)
    plt.savefig(output_dir / "roc_curves.png", dpi=150, bbox_inches="tight")
    plt.close()
    log(f"saved roc_curves.png → {output_dir}")

    # ==================================================================
    # Tile-level test predictions
    # ==================================================================
    test_path = Path(test_dir)
    if test_path.exists():
        test_images = sorted(
            p for p in test_path.rglob("*")
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff")
        )
        if test_images:
            log(f"running tile-level test predictions ({len(test_images)} tiles)")
            counts = {cls: 0 for cls in dls.vocab}
            results = []

            for img_path in test_images:
                # infer true label from subfolder name (if organized by class)
                true_label = img_path.parent.name if img_path.parent != test_path else ""
                pred, pred_idx, probs = learn.predict(img_path)
                pred_label = str(pred)
                counts[pred_label] = counts.get(pred_label, 0) + 1
                results.append({
                    "tile": str(img_path),
                    "true_label": true_label,
                    "prediction": pred_label,
                    "confidence": float(probs[pred_idx]),
                })

            pd.DataFrame(results).to_csv(
                output_dir / "test_predictions.csv", index=False,
            )
            pd.DataFrame([counts]).to_csv(
                output_dir / "test_counts_summary.csv", index=False,
            )
            log(f"test counts: {counts}")
        else:
            log(f"no image files found in {test_path} — skipping test inference")
    else:
        log(f"test directory not found ({test_path}) — skipping test inference")

    # ==================================================================
    # WSI inference (optional)
    # ==================================================================
    wsi_cfg = cfg.get("wsi", {})
    wsi_dir = repo / wsi_cfg.get("wsi_dir", "data/wsi")
    wsi_level = int(wsi_cfg.get("level", 1))
    download_script = wsi_cfg.get("download_script", "scripts/download_mother_nmr.sh")

    if args.skip_wsi:
        log("skipping WSI inference (--skip-wsi)")
    else:
        log("starting WSI inference")
        wsi_dir.mkdir(parents=True, exist_ok=True)
        tif_files = list(wsi_dir.rglob("*.tif"))

        if not tif_files:
            log("no .tif files found — attempting download script")
            try:
                subprocess.run(["bash", download_script], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                log(f"download script failed: {exc}")
                log(f"place .tif files manually in {wsi_dir}")
                tif_files = []
            else:
                tif_files = list(wsi_dir.rglob("*.tif"))

        all_results = []
        log(f"found {len(tif_files)} .tif files for WSI inference (level={wsi_level})")
        for slide_path in tif_files:
            try:
                output = analyze_wsi(slide_path, learn, level=wsi_level)
                if output is None:
                    continue

                slide_counts, spatial = output
                slide_name = slide_path.stem
                log(f"  {slide_name}: {slide_counts}")

                pd.DataFrame([slide_counts]).to_csv(
                    output_dir / f"{slide_name}_counts.csv", index=False,
                )
                pd.DataFrame(spatial).to_csv(
                    output_dir / f"{slide_name}_spatial.csv", index=False,
                )
                all_results.append({"slide": slide_name, **slide_counts})
            except Exception as exc:
                log(f"  ERROR processing {slide_path.name}: {exc} — skipping")
                continue

        if all_results:
            pd.DataFrame(all_results).to_csv(
                output_dir / "all_slides_summary.csv", index=False,
            )

    log("pipeline complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())