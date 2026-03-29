#!/usr/bin/env python3
"""
EDA/05_make_presentation_figs.py

Generate results figures from CNN pipeline outputs.

Reads actual pipeline artifacts (not hardcoded values):
  - outputs/logs/pipeline_*.log       → training curves (loss, error_rate)
  - outputs/test_predictions.csv       → test set prediction distribution
  - outputs/test_counts_summary.csv    → test class counts
  - outputs/all_slides_summary.csv     → WSI-level prediction counts
  - data/processed/H_glaber/train/     → training class distribution

Outputs (all written to outputs/figures/results/):
  - fig1_class_distribution.png
  - fig2_training_curves.png
  - fig3_test_predictions.png
  - fig4_wsi_proportions.png
  - fig5_wsi_heatmap.png
  - fig6_slide_size_vs_tiles.png

Run from repo root:
  python explore/05_make_presentation_figs.py

Override paths:
  python explore/05_make_presentation_figs.py \
    --log outputs/logs/pipeline_run_20260328_202129.log \
    --test-predictions outputs/test_predictions.csv \
    --wsi-summary outputs/all_slides_summary.csv \
    --data-dir data/processed/H_glaber \
    --wsi-dir data/raw/H_glaber \
    --figdir outputs/figures/results

Debugging and code assistance were provided by Claude (Opus 4.6).
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.paths import find_repo_root


# ======================================================================
# Log parsing
# ======================================================================

def find_latest_log(logs_dir: Path) -> Optional[Path]:
    """Find the most recent pipeline_*.log file."""
    logs = sorted(logs_dir.glob("pipeline_*.log"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


def parse_training_log(log_path: Path) -> dict:
    """
    Parse the pipeline log for training metrics and class info.

    Returns dict with keys:
      - classes: list of class names
      - class_counts: dict[class_name] -> int (training tile counts)
      - class_weights: dict[class_name] -> float
      - phase1: list of dicts with epoch, train_loss, valid_loss, error_rate
      - phase2: list of dicts (same structure)
      - device: str
      - image_size: int
      - batch_size: int
    """
    text = log_path.read_text(encoding="utf-8")

    result = {
        "classes": [],
        "class_counts": {},
        "class_weights": {},
        "phase1": [],
        "phase2": [],
        "device": "unknown",
        "image_size": 224,
        "batch_size": 16,
    }

    # Extract device
    m = re.search(r"\[pipeline\] device:\s*(\S+)", text)
    if m:
        result["device"] = m.group(1)

    # Extract hyperparams
    m = re.search(r"image_size=(\d+)\s+bs=(\d+)", text)
    if m:
        result["image_size"] = int(m.group(1))
        result["batch_size"] = int(m.group(2))

    # Extract classes
    m = re.search(r"classes:\s*\[([^\]]+)\]", text)
    if m:
        result["classes"] = [c.strip().strip("'\"") for c in m.group(1).split(",")]

    # Extract per-class counts and weights
    for match in re.finditer(
        r"\[pipeline\]\s+([\w\s]+?):\s+(\d+)\s+train tiles,\s+weight=([\d.]+)", text
    ):
        cls = match.group(1).strip()
        result["class_counts"][cls] = int(match.group(2))
        result["class_weights"][cls] = float(match.group(3))

    # Parse epoch lines: "N  train_loss  valid_loss  error_rate  time"
    # Split by phase markers
    phase1_match = re.search(
        r"phase 1:.*?(?=phase 2:|$)", text, re.DOTALL
    )
    phase2_match = re.search(
        r"phase 2:.*?(?=pipeline complete|loading best|$)", text, re.DOTALL
    )

    epoch_pattern = re.compile(
        r"^(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+\d+:\d+",
        re.MULTILINE,
    )

    if phase1_match:
        for em in epoch_pattern.finditer(phase1_match.group()):
            result["phase1"].append({
                "epoch": int(em.group(1)),
                "train_loss": float(em.group(2)),
                "valid_loss": float(em.group(3)),
                "error_rate": float(em.group(4)),
            })

    if phase2_match:
        for em in epoch_pattern.finditer(phase2_match.group()):
            result["phase2"].append({
                "epoch": int(em.group(1)),
                "train_loss": float(em.group(2)),
                "valid_loss": float(em.group(3)),
                "error_rate": float(em.group(4)),
            })

    return result


# ======================================================================
# WSI metadata
# ======================================================================

def get_wsi_dimensions(wsi_dir: Path, log_path: Path) -> Dict[str, Tuple[int, int]]:
    """
    Extract slide dimensions from the pipeline log.
    Parses lines like: "slide array shape: 21727x13712 (level 1)"
    """
    dims = {}
    text = log_path.read_text(encoding="utf-8")

    # Match slide processing blocks
    blocks = re.findall(
        r"Processing:.*?/([^/]+)\.tif.*?slide array shape:\s*(\d+)x(\d+)",
        text, re.DOTALL,
    )
    for slide_stem, w, h in blocks:
        # Extract accession ID (MDB0000XXX)
        acc_match = re.search(r"(MDB\d+)", slide_stem)
        if acc_match:
            dims[acc_match.group(1)] = (int(w), int(h))

    return dims


def get_wsi_tile_counts(log_path: Path) -> Dict[str, int]:
    """Extract tissue tile counts per slide from log."""
    counts = {}
    text = log_path.read_text(encoding="utf-8")

    for match in re.finditer(
        r"Processing:.*?(MDB\d+).*?tissue tiles extracted:\s*(\d+)",
        text, re.DOTALL,
    ):
        counts[match.group(1)] = int(match.group(2))

    return counts


# ======================================================================
# Figure generators
# ======================================================================

def fig1_class_distribution(
    class_counts: Dict[str, int],
    class_weights: Dict[str, float],
    out_path: Path,
) -> None:
    """Training set class distribution with inverse-frequency weights."""
    classes = sorted(class_counts.keys(), key=lambda c: class_counts[c], reverse=True)
    counts = [class_counts[c] for c in classes]
    weights = [class_weights.get(c, 1.0) for c in classes]

    # Format labels with line breaks for long names
    labels = [c.replace("_", " ").replace(" ", "\n", 1).title() for c in classes]

    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(labels))
    width = 0.4

    bars1 = ax1.bar(x - width / 2, counts, width, color="#4C72B0", label="Training Tiles", edgecolor="white")
    ax1.set_ylabel("Number of Training Tiles", fontsize=11, color="#4C72B0")
    ax1.tick_params(axis="y", labelcolor="#4C72B0")

    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width / 2, weights, width, color="#DD8452", label="Class Weight", edgecolor="white")
    ax2.set_ylabel("Inverse-Frequency Weight", fontsize=11, color="#DD8452")
    ax2.tick_params(axis="y", labelcolor="#DD8452")
    ax2.axhline(y=1.0, color="gray", linestyle="--", alpha=0.5, linewidth=0.8)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_title("Training Set Class Distribution and Inverse-Frequency Weights",
                   fontsize=13, fontweight="bold", pad=12)

    for bar, count in zip(bars1, counts):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                 str(count), ha="center", va="bottom", fontsize=8, color="#4C72B0", fontweight="bold")
    for bar, w in zip(bars2, weights):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                 f"{w:.2f}", ha="center", va="bottom", fontsize=8, color="#DD8452", fontweight="bold")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", framealpha=0.9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path}")


def fig2_training_curves(
    phase1: List[dict],
    phase2: List[dict],
    out_path: Path,
) -> None:
    """Training and validation loss/error_rate curves across both phases."""
    if not phase1:
        print("  WARNING: no phase 1 data — skipping training curves")
        return

    # Build continuous epoch indices
    p1_epochs = list(range(len(phase1)))
    p1_train = [e["train_loss"] for e in phase1]
    p1_valid = [e["valid_loss"] for e in phase1]
    p1_err = [e["error_rate"] for e in phase1]

    p2_offset = len(phase1)
    p2_epochs = [p2_offset + i for i in range(len(phase2))]
    p2_train = [e["train_loss"] for e in phase2]
    p2_valid = [e["valid_loss"] for e in phase2]
    p2_err = [e["error_rate"] for e in phase2]

    all_epochs = p1_epochs + p2_epochs
    all_train = p1_train + p2_train
    all_valid = p1_valid + p2_valid
    all_err = p1_err + p2_err

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Loss curves
    ax1.plot(all_epochs, all_train, "o-", color="#4C72B0", label="Train Loss", markersize=5)
    ax1.plot(all_epochs, all_valid, "s-", color="#DD8452", label="Valid Loss", markersize=5)

    if phase2:
        boundary = p2_offset - 0.5
        y_top = max(max(all_train), max(all_valid)) * 1.05
        ax1.axvline(x=boundary, color="gray", linestyle="--", alpha=0.6, linewidth=1)
        ax1.text(np.mean(p1_epochs), y_top, "Phase 1\n(Frozen)", ha="center", fontsize=9, color="gray")
        ax1.text(np.mean(p2_epochs), y_top, "Phase 2\n(Unfrozen)", ha="center", fontsize=9, color="gray")

    ax1.set_xlabel("Epoch", fontsize=11)
    ax1.set_ylabel("Loss", fontsize=11)
    ax1.set_title("Training and Validation Loss", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=10)
    ax1.grid(alpha=0.3)
    ax1.set_xticks(all_epochs)

    # Error rate
    ax2.plot(all_epochs, [e * 100 for e in all_err], "D-", color="#55A868", markersize=5)

    if phase2:
        ax2.axvline(x=boundary, color="gray", linestyle="--", alpha=0.6, linewidth=1)
        err_top = max(all_err) * 100 * 1.15
        ax2.text(np.mean(p1_epochs), err_top, "Phase 1\n(Frozen)", ha="center", fontsize=9, color="gray")
        ax2.text(np.mean(p2_epochs), err_top, "Phase 2\n(Unfrozen)", ha="center", fontsize=9, color="gray")

    ax2.set_xlabel("Epoch", fontsize=11)
    ax2.set_ylabel("Error Rate (%)", fontsize=11)
    ax2.set_title("Validation Error Rate", fontsize=12, fontweight="bold")
    ax2.grid(alpha=0.3)
    ax2.set_xticks(all_epochs)

    # Annotate best epoch
    best_idx = int(np.argmin(all_err))
    best_err = all_err[best_idx] * 100
    ax2.annotate(
        f"Best model\n({best_err:.1f}%)",
        xy=(all_epochs[best_idx], best_err),
        xytext=(all_epochs[best_idx] - 1.5, best_err + 15),
        arrowprops=dict(arrowstyle="->", color="#C44E52"),
        fontsize=9, color="#C44E52", ha="center", fontweight="bold",
    )

    # Annotate early stopping if phase 2 exists
    if phase2:
        last_err = all_err[-1] * 100
        ax2.annotate(
            "Early stop",
            xy=(all_epochs[-1], last_err),
            xytext=(all_epochs[-1] - 1, last_err + 15),
            arrowprops=dict(arrowstyle="->", color="#C44E52"),
            fontsize=9, color="#C44E52", ha="center",
        )

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path}")


def fig3_test_predictions(test_csv: Path, out_path: Path) -> None:
    """Test set prediction distribution bar chart."""
    df = pd.read_csv(test_csv)

    counts = df["prediction"].value_counts().sort_index()
    labels = [c.replace("_", " ").replace(" ", "\n", 1).title() for c in counts.index]

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = plt.cm.Set2(np.linspace(0, 1, len(counts)))
    bars = ax.bar(labels, counts.values, color=colors, edgecolor="white", linewidth=0.8)

    for bar, count in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(count), ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_ylabel("Number of Tiles", fontsize=11)
    ax.set_title(f"Test Set Predictions ({len(df)} Tiles)", fontsize=13, fontweight="bold", pad=10)
    ax.set_ylim(0, max(counts.values) * 1.3)
    ax.grid(axis="y", alpha=0.3)
    ax.tick_params(axis="x", labelsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path}")


def fig4_wsi_proportions(
    wsi_df: pd.DataFrame,
    tile_counts: Dict[str, int],
    out_path: Path,
) -> None:
    """Stacked bar chart of WSI prediction proportions per slide."""
    slides = sorted(wsi_df["slide"].tolist())
    class_cols = [c for c in wsi_df.columns if c != "slide"]

    # Build proportion matrix
    totals = []
    for slide in slides:
        acc = re.search(r"(MDB\d+)", slide)
        acc_id = acc.group(1) if acc else slide
        totals.append(tile_counts.get(acc_id, wsi_df.loc[wsi_df["slide"] == slide, class_cols].sum(axis=1).values[0]))

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(slides))
    bottom = np.zeros(len(slides))

    cmap_colors = ["#4C72B0", "#C44E52", "#8172B2", "#CCB974",
                   "#55A868", "#DD8452", "#64B5CD", "#DA8BC3"]

    for i, cls in enumerate(class_cols):
        vals = []
        for slide in slides:
            row = wsi_df[wsi_df["slide"] == slide]
            count = int(row[cls].values[0]) if cls in row.columns else 0
            total = totals[slides.index(slide)]
            vals.append(count / max(total, 1) * 100)

        color = cmap_colors[i % len(cmap_colors)]
        ax.bar(x, vals, bottom=bottom, label=cls.replace("_", " ").title(),
               color=color, edgecolor="white", linewidth=0.3)
        bottom += np.array(vals)

    # Format x labels with slide ID and tile count
    x_labels = []
    for slide, total in zip(slides, totals):
        acc = re.search(r"(MDB\d+)", slide)
        label = acc.group(1) if acc else slide
        x_labels.append(f"{label}\n(n={total})")

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=8)
    ax.set_ylabel("Proportion of Tissue Tiles (%)", fontsize=11)
    ax.set_title("WSI-Level Prediction Distribution Across All Slides",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9, framealpha=0.9)
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.2)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path}")


def fig5_wsi_heatmap(
    wsi_df: pd.DataFrame,
    tile_counts: Dict[str, int],
    out_path: Path,
) -> None:
    """Heatmap of absolute prediction counts by class and slide."""
    slides = sorted(wsi_df["slide"].tolist())
    class_cols = [c for c in wsi_df.columns if c != "slide"]

    data_matrix = np.zeros((len(class_cols), len(slides)))
    for j, slide in enumerate(slides):
        row = wsi_df[wsi_df["slide"] == slide]
        for i, cls in enumerate(class_cols):
            data_matrix[i, j] = int(row[cls].values[0]) if cls in row.columns else 0

    totals = []
    for slide in slides:
        acc = re.search(r"(MDB\d+)", slide)
        acc_id = acc.group(1) if acc else slide
        totals.append(tile_counts.get(acc_id, int(data_matrix[:, slides.index(slide)].sum())))

    fig, ax = plt.subplots(figsize=(12, 5.5))
    display_data = np.where(data_matrix == 0, 0.5, data_matrix)
    norm = mcolors.LogNorm(vmin=1, vmax=max(data_matrix.max(), 2))

    im = ax.imshow(display_data, aspect="auto", cmap="YlOrRd", norm=norm)

    x_labels = []
    for slide, total in zip(slides, totals):
        acc = re.search(r"(MDB\d+)", slide)
        label = acc.group(1) if acc else slide
        x_labels.append(f"{label}\n(n={total})")

    ax.set_xticks(np.arange(len(slides)))
    ax.set_xticklabels(x_labels, fontsize=8)
    ax.set_yticks(np.arange(len(class_cols)))
    ax.set_yticklabels([c.replace("_", " ").title() for c in class_cols], fontsize=9)

    for i in range(len(class_cols)):
        for j in range(len(slides)):
            val = int(data_matrix[i, j])
            color = "white" if val > 100 else "black"
            ax.text(j, i, str(val), ha="center", va="center",
                    fontsize=8, color=color, fontweight="bold")

    ax.set_title("WSI Tile Prediction Counts by Class and Slide (Log Scale)",
                 fontsize=13, fontweight="bold", pad=12)
    plt.colorbar(im, ax=ax, label="Tile Count", shrink=0.8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path}")


def fig6_slide_size_vs_tiles(
    slide_dims: Dict[str, Tuple[int, int]],
    tile_counts: Dict[str, int],
    out_path: Path,
) -> None:
    """Scatter plot of slide area vs tissue tile yield."""
    common_slides = sorted(set(slide_dims.keys()) & set(tile_counts.keys()))
    if len(common_slides) < 2:
        print("  WARNING: not enough slides with both dimensions and tile counts — skipping")
        return

    megapixels = [slide_dims[s][0] * slide_dims[s][1] / 1e6 for s in common_slides]
    tiles = [tile_counts[s] for s in common_slides]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(megapixels, tiles, s=100, c="#4C72B0", edgecolors="white", linewidth=1.5, zorder=5)

    for i, slide in enumerate(common_slides):
        short = slide.replace("MDB000", "")
        ax.annotate(short, (megapixels[i], tiles[i]),
                    textcoords="offset points", xytext=(8, 5), fontsize=8, color="gray")

    # Linear fit
    z = np.polyfit(megapixels, tiles, 1)
    p = np.poly1d(z)
    x_line = np.linspace(min(megapixels), max(megapixels), 100)
    ax.plot(x_line, p(x_line), "--", color="#DD8452", alpha=0.7, linewidth=1.5, label="Linear fit")

    r = np.corrcoef(megapixels, tiles)[0, 1]
    ax.text(0.05, 0.92, f"r = {r:.3f}", transform=ax.transAxes,
            fontsize=11, fontweight="bold", color="#DD8452")

    ax.set_xlabel("Slide Area at Level 1 (Megapixels)", fontsize=11)
    ax.set_ylabel("Tissue Tiles Extracted", fontsize=11)
    ax.set_title("Slide Size vs. Tissue Tile Yield", fontsize=13, fontweight="bold", pad=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path}")


# ======================================================================
# Main
# ======================================================================

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate results figures from CNN pipeline outputs."
    )
    ap.add_argument("--log", default=None,
                    help="Path to pipeline log. Default: latest outputs/logs/pipeline_*.log")
    ap.add_argument("--test-predictions", default="outputs/test_predictions.csv")
    ap.add_argument("--wsi-summary", default="outputs/all_slides_summary.csv")
    ap.add_argument("--data-dir", default="data/processed/H_glaber")
    ap.add_argument("--wsi-dir", default="data/raw/H_glaber")
    ap.add_argument("--figdir", default="outputs/figures/results")
    args = ap.parse_args()

    repo = find_repo_root()
    figdir = repo / args.figdir
    figdir.mkdir(parents=True, exist_ok=True)

    # Find pipeline log
    if args.log:
        log_path = repo / args.log
    else:
        log_path = find_latest_log(repo / "outputs" / "logs")

    if log_path is None or not log_path.exists():
        print("[ERROR] No pipeline log found. Run the CNN pipeline first:")
        print("  bash scripts/run_cnn_pipeline.sh")
        return 2

    print(f"[results] Using log: {log_path}")
    parsed = parse_training_log(log_path)

    # ---- Figure 1: Class distribution ----
    if parsed["class_counts"]:
        print("[results] Figure 1: class distribution")
        fig1_class_distribution(
            parsed["class_counts"],
            parsed["class_weights"],
            figdir / "fig1_class_distribution.png",
        )
    else:
        # Fallback: count files in data_dir/train/
        print("[results] Figure 1: counting files in training directory")
        train_dir = repo / args.data_dir / "train"
        if train_dir.exists():
            image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
            counts = {}
            for cls_dir in sorted(train_dir.iterdir()):
                if cls_dir.is_dir():
                    n = sum(1 for f in cls_dir.iterdir() if f.suffix.lower() in image_exts)
                    counts[cls_dir.name] = n
            if counts:
                # Compute weights (same formula as cnn_pipeline.py)
                arr = np.array(list(counts.values()), dtype=np.float64)
                w = 1.0 / np.maximum(arr, 1)
                w = w / w.sum() * len(w)
                weights = dict(zip(counts.keys(), w))
                fig1_class_distribution(counts, weights, figdir / "fig1_class_distribution.png")

    # ---- Figure 2: Training curves ----
    if parsed["phase1"]:
        print("[results] Figure 2: training curves")
        fig2_training_curves(
            parsed["phase1"],
            parsed["phase2"],
            figdir / "fig2_training_curves.png",
        )
    else:
        print("[WARNING] No training metrics found in log — skipping Figure 2")

    # ---- Figure 3: Test predictions ----
    test_csv = repo / args.test_predictions
    if test_csv.exists():
        print("[results] Figure 3: test predictions")
        fig3_test_predictions(test_csv, figdir / "fig3_test_predictions.png")
    else:
        print(f"[WARNING] {test_csv} not found — skipping Figure 3")

    # ---- Figures 4-6: WSI results ----
    wsi_csv = repo / args.wsi_summary
    if wsi_csv.exists():
        print("[results] Figures 4-6: WSI results")
        wsi_df = pd.read_csv(wsi_csv)

        tile_counts = get_wsi_tile_counts(log_path)
        slide_dims = get_wsi_dimensions(repo / args.wsi_dir, log_path)

        fig4_wsi_proportions(wsi_df, tile_counts, figdir / "fig4_wsi_proportions.png")
        fig5_wsi_heatmap(wsi_df, tile_counts, figdir / "fig5_wsi_heatmap.png")

        if slide_dims:
            fig6_slide_size_vs_tiles(slide_dims, tile_counts, figdir / "fig6_slide_size_vs_tiles.png")
        else:
            print("[WARNING] No slide dimensions found in log — skipping Figure 6")
    else:
        print(f"[WARNING] {wsi_csv} not found — skipping Figures 4-6")
        print("  (WSI inference may have been skipped with --skip-wsi)")

    print(f"\n[results] All figures written to: {figdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())