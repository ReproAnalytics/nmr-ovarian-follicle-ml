#!/usr/bin/env python3
"""
Ovarian Follicle Classification Pipeline
-----------------------------------------
ResNet34 transfer-learning classifier for histological tile images,
with whole-slide image (WSI) inference support.

Usage:
    python cnn_pipeline.py --data_dir ./CNN --test_dir ./CNN/test --wsi_dir ./CNN/wsi
"""

import argparse
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for terminal; switch to "TkAgg" if you want popups
import matplotlib.pyplot as plt
import torch
import openslide
from PIL import Image

from fastai.vision.all import (
    ImageDataLoaders, Resize, Normalize, imagenet_stats,
    cnn_learner, resnet34, error_rate, ClassificationInterpretation,
)
from fastai.callback.tracker import EarlyStoppingCallback, SaveModelCallback
from sklearn.metrics import roc_curve, auc


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Ovarian follicle CNN pipeline")
    parser.add_argument("--data_dir", type=str, default="./CNN",
                        help="Root directory containing train/ and valid/ subfolders")
    parser.add_argument("--test_dir", type=str, default="./CNN/test",
                        help="Directory with test tile PNGs")
    parser.add_argument("--wsi_dir", type=str, default="./CNN/wsi",
                        help="Directory with WSI .tif files")
    parser.add_argument("--download_script", type=str, default="scripts/download_mother_nmr.sh",
                        help="Bash script to download WSI files from MOTHER database")
    parser.add_argument("--output_dir", type=str, default="./results",
                        help="Directory to save all CSV and figure outputs")
    parser.add_argument("--epochs_head", type=int, default=5,
                        help="Epochs for frozen fine-tune phase")
    parser.add_argument("--epochs_full", type=int, default=10,
                        help="Epochs for unfrozen training phase")
    parser.add_argument("--bs", type=int, default=16, help="Batch size")
    parser.add_argument("--tile_size", type=int, default=224, help="Tile dimensions (px)")
    parser.add_argument("--wsi_level", type=int, default=1,
                        help="OpenSlide pyramid level for WSI tiling")
    parser.add_argument("--skip_wsi", action="store_true",
                        help="Skip the WSI inference stage")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Tissue detection & WSI tiling
# ---------------------------------------------------------------------------
def is_tissue(tile, threshold=220):
    """Simple mean-intensity background filter."""
    return np.mean(np.array(tile)) < threshold


def tile_wsi(slide, level=0, tile_size=224, stride=224):
    """Extract tissue-containing tiles from a whole-slide image."""
    width, height = slide.level_dimensions[level]
    tiles, coords = [], []

    for y in range(0, height - tile_size, stride):
        for x in range(0, width - tile_size, stride):
            tile = slide.read_region((x, y), level, (tile_size, tile_size)).convert("RGB")
            if is_tissue(tile):
                tiles.append(tile)
                coords.append((x, y))

    return tiles, coords


# ---------------------------------------------------------------------------
# WSI-level inference
# ---------------------------------------------------------------------------
def analyze_wsi(slide_path, learn, level=1):
    """Run trained model over every tissue tile in a WSI."""
    print(f"\nProcessing: {slide_path}")
    slide = openslide.OpenSlide(str(slide_path))
    tiles, coords = tile_wsi(slide, level=level)

    if len(tiles) == 0:
        print("  No tissue detected.")
        return None

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


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main():
    args = parse_args()

    data_path = Path(args.data_dir).expanduser().resolve()
    test_dir = Path(args.test_dir).expanduser().resolve()
    wsi_dir = Path(args.wsi_dir).expanduser().resolve()
    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # ------------------------------------------------------------------
    # 1. Build DataLoaders
    # ------------------------------------------------------------------
    print("\n=== Building DataLoaders ===")
    dls = ImageDataLoaders.from_folder(
        data_path,
        train="train",
        valid="valid",
        item_tfms=Resize(args.tile_size),
        batch_tfms=Normalize.from_stats(*imagenet_stats),
        bs=args.bs,
    )
    print("Classes:", dls.vocab)

    # ------------------------------------------------------------------
    # 2. Create learner
    # ------------------------------------------------------------------
    print("\n=== Initialising ResNet34 learner ===")
    learn = cnn_learner(dls, resnet34, metrics=error_rate)
    learn.model.to(device)

    # ------------------------------------------------------------------
    # 3. Frozen fine-tune (head only)
    # ------------------------------------------------------------------
    print(f"\n=== Fine-tuning head ({args.epochs_head} epochs) ===")
    learn.fine_tune(
        args.epochs_head,
        base_lr=1e-3,
        cbs=[
            EarlyStoppingCallback(monitor="valid_loss", patience=3),
            SaveModelCallback(monitor="valid_loss", fname="best_resnet34"),
        ],
    )

    # ------------------------------------------------------------------
    # 4. Unfrozen full training
    # ------------------------------------------------------------------
    print(f"\n=== Unfrozen training ({args.epochs_full} epochs) ===")
    learn.unfreeze()
    learn.fit_one_cycle(
        args.epochs_full,
        lr_max=slice(1e-5, 1e-3),
        cbs=[
            EarlyStoppingCallback(monitor="valid_loss", patience=3),
            SaveModelCallback(monitor="valid_loss", fname="best_resnet34"),
        ],
    )

    # ------------------------------------------------------------------
    # 5. Load best checkpoint & evaluate
    # ------------------------------------------------------------------
    print("\n=== Loading best model & evaluating ===")
    learn.load("best_resnet34")
    learn.model.eval()

    interp = ClassificationInterpretation.from_learner(learn)

    # Confusion matrix
    fig_cm = interp.plot_confusion_matrix()
    plt.savefig(out_dir / "confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close()

    # Top losses
    interp.plot_top_losses(5)
    plt.savefig(out_dir / "top_losses.png", dpi=150, bbox_inches="tight")
    plt.close()

    # ------------------------------------------------------------------
    # 6. Multi-class ROC curve
    # ------------------------------------------------------------------
    print("\n=== Generating ROC curves ===")
    preds_val, targs_val = learn.get_preds()
    print(f"Prediction classes: {dls.vocab}")

    plt.figure(figsize=(10, 8))
    for i, class_name in enumerate(dls.vocab):
        fpr, tpr, _ = roc_curve((targs_val == i).numpy(), preds_val[:, i].numpy())
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
    plt.savefig(out_dir / "roc_curves.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved → {out_dir / 'roc_curves.png'}")

    # ------------------------------------------------------------------
    # 7. Tile-level test predictions
    # ------------------------------------------------------------------
    if test_dir.exists():
        print("\n=== Running tile-level test predictions ===")
        counts = {cls: 0 for cls in dls.vocab}
        results = []

        for img_path in sorted(test_dir.glob("*.png")):
            pred, pred_idx, probs = learn.predict(img_path)
            counts[str(pred)] += 1
            results.append({
                "tile": str(img_path),
                "prediction": str(pred),
                "confidence": float(probs[pred_idx]),
            })

        pd.DataFrame(results).to_csv(out_dir / "tile_predictions.csv", index=False)
        pd.DataFrame([counts]).to_csv(out_dir / "tile_counts_summary.csv", index=False)
        print("Tile counts:", counts)
    else:
        print(f"\n⚠  Test directory not found ({test_dir}); skipping tile-level inference.")

    # ------------------------------------------------------------------
    # 8. WSI inference (optional)
    # ------------------------------------------------------------------
    if args.skip_wsi:
        print("\n=== Skipping WSI inference (--skip_wsi) ===")
    else:
        print("\n=== WSI inference ===")
        wsi_dir.mkdir(parents=True, exist_ok=True)

        tif_files = list(wsi_dir.rglob("*.tif"))

        if len(tif_files) == 0:
            print("No WSI .tif files found. Running download script...")
            try:
                subprocess.run(["bash", args.download_script], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                print(f"  Download script failed: {exc}")
                print("  Place .tif files manually in", wsi_dir)
                tif_files = []
            else:
                tif_files = list(wsi_dir.rglob("*.tif"))

        all_results = []
        for slide_path in tif_files:
            output = analyze_wsi(slide_path, learn, level=args.wsi_level)
            if output is None:
                continue

            slide_counts, spatial = output
            slide_name = slide_path.stem

            print(f"  {slide_name}: {slide_counts}")

            pd.DataFrame([slide_counts]).to_csv(out_dir / f"{slide_name}_counts.csv", index=False)
            pd.DataFrame(spatial).to_csv(out_dir / f"{slide_name}_spatial.csv", index=False)

            all_results.append({"slide": slide_name, **slide_counts})

        if all_results:
            pd.DataFrame(all_results).to_csv(out_dir / "all_slides_summary.csv", index=False)

    print("\n✓ Pipeline complete.  Outputs saved to:", out_dir)


if __name__ == "__main__":
    main()