#!/usr/bin/env python3
"""
metadata_cellcountdata.py

Merge QuPath nuclei measurements with MOTHER slide metadata and compute
per-donor morphological diversity metrics.

Usage
-----
    # default: reads pipeline-generated outputs/reports/dataset_inventory.csv
    python metadata_cellcountdata.py

    # override metadata path explicitly
    python metadata_cellcountdata.py --metadata path/to/dataset_inventory.csv

    # point at a different nuclei directory (default: current working directory)
    python metadata_cellcountdata.py --nuclei-dir /path/to/nuclei/csvs
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # non-interactive backend; safe in WSL / headless
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import spearmanr

# ------------------------------------------------------------------
# Repo-root resolution  (mirrors src/utils/paths.py)
# ------------------------------------------------------------------
_MARKERS = ("configs", "src", ".git", "README.md")


def _find_repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for _ in range(10):
        if any((cur / m).exists() for m in _MARKERS):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    # Fallback: directory containing this script
    return Path(__file__).resolve().parent


_REPO = _find_repo_root()

# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
ap = argparse.ArgumentParser(description="Metadata + QuPath cell-count analysis")
ap.add_argument(
    "--metadata",
    default=str(_REPO / "outputs" / "reports" / "dataset_inventory.csv"),
    help=(
        "Path to dataset_inventory.csv produced by the pipeline "
        "(default: outputs/reports/dataset_inventory.csv)"
    ),
)
ap.add_argument(
    "--nuclei-dir",
    default=".",
    help="Directory containing nuclei_*.csv files exported from QuPath (default: cwd)",
)
ap.add_argument(
    "--output",
    default=str(_REPO / "outputs" / "reports" / "celldata_metadata_combined.csv"),
    help="Output CSV path (default: outputs/reports/celldata_metadata_combined.csv)",
)
args = ap.parse_args()

# ------------------------------------------------------------------
# Load QuPath nuclei measurements
# ------------------------------------------------------------------
nuclei_pattern = os.path.join(args.nuclei_dir, "nuclei_*.csv")
nuclei_files = glob.glob(nuclei_pattern)

if not nuclei_files:
    print(f"ERROR: no nuclei_*.csv files found matching: {nuclei_pattern}", file=sys.stderr)
    sys.exit(1)

nuclei_list = []
for file in nuclei_files:
    df = pd.read_csv(file, sep="\t")
    df["source_file"] = os.path.basename(file)
    nuclei_list.append(df)

cells = pd.concat(nuclei_list, ignore_index=True)
print("Total cells:", len(cells))
print(cells.columns.tolist())

# ------------------------------------------------------------------
# Load pipeline-generated metadata  (was hardcoded to ~/data_sci/...)
# ------------------------------------------------------------------
metadata_path = Path(args.metadata)
if not metadata_path.exists():
    print(
        f"ERROR: metadata file not found: {metadata_path}\n"
        "       Run 'python EDA/00_dataset_sanity.py' to generate it, or pass\n"
        "       --metadata <path> to specify a custom location.",
        file=sys.stderr,
    )
    sys.exit(1)

metadata = pd.read_csv(metadata_path)

# Keep only relevant metadata columns
metadata = metadata[[
    "tiff_candidates",
    "donorYears",
    "donorDays",
    "donorSex",
    "donorLifeStage",
]]

print(metadata.head())

# ------------------------------------------------------------------
# Merge
# ------------------------------------------------------------------
print("cells  tiff_candidates sample:", cells["tiff_candidates"].unique()[:5])
print("meta   tiff_candidates sample:", metadata["tiff_candidates"].unique()[:5])

cells = cells.merge(metadata, on="tiff_candidates", how="left")

print(cells[["tiff_candidates", "donorYears"]].head())
print("Total cells:", len(cells))
print("Unique specimens:", cells["tiff_candidates"].nunique())
print("Unique ages:", cells["donorYears"].unique())

# ------------------------------------------------------------------
# Clean and save merged data
# ------------------------------------------------------------------
cells["Nucleus: Area"] = pd.to_numeric(cells["Nucleus: Area"], errors="coerce")
cells = cells.dropna(subset=["Nucleus: Area"])
cells = cells.drop(columns=["Object ID"], errors="ignore")

output_path = Path(args.output)
output_path.parent.mkdir(parents=True, exist_ok=True)
cells.to_csv(output_path, index=False)
print(f"Saved merged data -> {output_path}")

# ------------------------------------------------------------------
# Donor-level morphological diversity
# ------------------------------------------------------------------

donor_div = cells.groupby("tiff_candidates").agg(
    donorYears=("donorYears", "first"),
    donorDays=("donorDays", "first"),
    nuc_mean=("Nucleus: Area", "mean"),
    nuc_std=("Nucleus: Area", "std"),
)
donor_div["nuc_cv"] = donor_div["nuc_std"] / donor_div["nuc_mean"]

shape_div = cells.groupby("tiff_candidates").agg(
    circ_sd=("Nucleus: Circularity", "std"),
    ecc_sd=("Nucleus: Eccentricity", "std"),
)
donor_div = donor_div.merge(shape_div, on="tiff_candidates")

intensity_div = cells.groupby("tiff_candidates").agg(
    hemo_sd=("Nucleus: Hematoxylin OD mean", "std"),
    dab_sd=("Nucleus: DAB OD mean", "std"),
)
donor_div = donor_div.merge(intensity_div, on="tiff_candidates")

# Age normalisation: prefer donorYears; fall back to donorDays / 365
donor_div["age_years"] = pd.to_numeric(donor_div["donorYears"], errors="coerce")
donor_div.loc[donor_div["age_years"].isna(), "age_years"] = (
    pd.to_numeric(donor_div["donorDays"], errors="coerce") / 365
)

print(donor_div.head())

# ------------------------------------------------------------------
# Composite diversity score
# ------------------------------------------------------------------
features = ["nuc_cv", "circ_sd", "ecc_sd", "hemo_sd", "dab_sd"]
scaled = (donor_div[features] - donor_div[features].mean()) / donor_div[features].std()
donor_div["composite_diversity"] = scaled.mean(axis=1)

# ------------------------------------------------------------------
# Spearman correlation: age vs composite diversity
# ------------------------------------------------------------------
valid = donor_div.dropna(subset=["age_years", "composite_diversity"])
rho, p = spearmanr(valid["age_years"], valid["composite_diversity"])

print("Composite diversity vs age")
print("rho =", round(rho, 3))
print("p   =", round(p, 4))

# ------------------------------------------------------------------
# Visualisation
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6, 5))
sns.regplot(
    x="age_years",
    y="composite_diversity",
    data=donor_div,
    scatter_kws={"s": 80},
    ax=ax,
)
ax.set_xlabel("Age (years)")
ax.set_ylabel("Composite Morphological Diversity")
ax.set_title("Age vs Ovarian Morphological Heterogeneity")
fig.tight_layout()

fig_path = _REPO / "outputs" / "figures" / "age_vs_morphological_diversity.png"
fig_path.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(fig_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Saved figure -> {fig_path}")