# NMR Ovarian Follicle ML

This project develops a machine-learning pipeline for automated identification and quantification of ovarian follicles in histological images of naked mole rats (*Heterocephalus glaber*).
The pipeline uses whole-slide images from the [MOTHER repository](https://mother-db.org/) and trains a pretrained **ResNet34** classifier (via [fastai](https://docs.fast.ai/)) to classify follicle types in PAS-stained ovarian tissue imaged at 40× magnification on a Zeiss AxioImager M2.

The repository is designed for **reproducible, team-based research**, with a clear separation between reusable library code, executable pipeline stages, configuration files, and generated outputs.

## Quickstart

This project is designed so that **everyone runs the same commands**.
You do **not** need to call Python files directly.

### Prerequisites

- Python 3.10+ available as `python`
- WSL / Linux / macOS
- [QuPath 0.5+](https://qupath.github.io/) for follicle annotation (GUI only — not required for training or inference)

### One-time setup (or when environment breaks)

```bash
# Clone the repo
git clone git@github.com:ReproAnalytics/nmr-ovarian-follicle-ml.git
cd nmr-ovarian-follicle-ml

# Run setup (creates .venv, installs dependencies, creates directories)
bash scripts/setup_env.sh

# Check environment health
bash scripts/doctor.sh
```

This will:

- create/activate a local virtual environment (.venv)
- install all Python dependencies
- verify your setup
- print the next recommended steps

## Run Pipeline

```bash
# Run the full pipeline end-to-end
bash scripts/run_pipeline.sh

# Or run individual stages
bash scripts/run_ingest.sh              # 1. Download WSIs + build manifest
bash scripts/run_preprocess.sh          # 2. Tile WSIs into patches
# ── manual QuPath annotation happens here ──
bash scripts/run_annotate.sh            # 3. Validate/consolidate QuPath exports
bash scripts/run_organize_splits.sh     # 4. Organize labeled tiles into folder layout
bash scripts/run_cnn_pipeline.sh        # 5. Train ResNet34 + evaluate (+ optional WSI inference)
bash scripts/run_postprocess_count.sh   # 6. Aggregate tile predictions → slide-level counts
```

Run stages after QuPath

```bash
bash scripts/run_pipeline.sh --from train
```

### EDA (Exploratory)

```bash
source .venv/bin/activate
python explore/00_dataset_sanity.py --raw-root data/raw/H_glaber
python explore/01_view_tiles.py
```

## Model Overview

The CNN pipeline (`run/cnn_pipeline.py`) uses **ResNet34** pretrained on ImageNet, fine-tuned with fastai in two phases:

1. **Frozen fine-tune** — trains only the classification head (default: 5 epochs, lr=1e-3)
2. **Unfrozen training** — trains all layers with discriminative learning rates (default: 10 epochs, lr=1e-5 to 1e-3)

Early stopping and best-model checkpointing are applied in both phases. Evaluation outputs include a confusion matrix, top-loss visualizations, per-class ROC curves with AUC scores, and optional whole-slide image inference with spatial prediction maps.

All training parameters are controlled through `configs/train.yaml`.

## Data Pipeline Flow

```text
MOTHER DB
    │
    ▼
[ingest.py] ─── download + manifest ──→ data/raw/H_glaber/
    │                                       H_glaber_manifest.csv
    ▼
[preprocess.py] ─── tile WSIs ──→ data/interim/tiles/
    │                                  tiles_manifest.csv
    ▼
[QuPath GUI] ─── manual annotation ──→ annotations/raw_exports/
    │
    ▼
[validate_exports.py] ─── consolidate ──→ annotations/gold_set/labeled_tiles.csv
    │
    ▼
[organize_splits.py] ─── folder layout ──→ data/processed/H_glaber/
    │                                          train/class_name/*.png
    │                                          valid/class_name/*.png
    │                                          test/class_name/*.png
    ▼
[cnn_pipeline.py] ─── train + eval ──→ outputs/
    │                                      models/run_*/best_resnet34.pth
    │                                      confusion_matrix.png
    │                                      roc_curves.png
    │                                      top_losses.png
    │                                      test_predictions.csv
    │                                      (optional WSI inference CSVs)
    ▼
[postprocess_count.py] ─── aggregate ──→ outputs/predictions/
                                             slide_level_predictions.csv
```

## Repository Structure

```text
nmr-ovarian-follicle-ml/
│
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── .gitignore
├── .gitattributes
│
├── environment/                         # environment reproducibility
│   ├── requirements.txt
│   └── setup_env.sh
│
├── configs/                             # stage-specific pipeline configuration
│   ├── dataset.yaml                     # ingest + raw data config
│   ├── preprocess.yaml                  # preprocessing + tile settings
│   ├── annotate.yaml                    # export validation / label joining rules
│   ├── train.yaml                       # ResNet34 model + hyperparameters + WSI config
│   ├── infer.yaml                       # standalone re-inference configuration
│   └── postprocess.yaml                 # follicle counting logic
│
├── data/                                # pipeline data states (gitignored)
│   ├── raw/                             # ingest.py writes here
│   │   └── H_glaber/
│   │       ├── <accession_id>/
│   │       │   ├── *.tif
│   │       │   ├── *.xml
│   │       │   └── *.png (previews)
│   │       └── H_glaber_manifest.csv
│   │
│   ├── interim/                         # preprocess.py writes here
│   │   └── tiles/
│   │       └── H_glaber/
│   │           └── <accession_id>/
│   │               ├── tile_x_y.png
│   │               └── ...
│   │
│   └── processed/                       # organize_splits.py writes here
│       └── H_glaber/
│           ├── train/
│           │   ├── primordial/*.png
│           │   ├── primary/*.png
│           │   ├── stroma/*.png
│           │   └── transitional_primordial/*.png
│           ├── valid/
│           │   └── (same class subfolders)
│           └── test/
│               └── (same class subfolders)
│
├── QuPath/                              # QuPath annotation stage
│   ├── project/                         # created/updated by bash launcher
│   └── scripts/
│       ├── import_images.groovy         # import images from data/raw/H_glaber
│       ├── export_annotations.groovy    # export annotations back to repo
│       └── export_measurements.groovy   # export measurements back to repo
│
├── annotations/                         # human supervision layer
│   ├── protocol.md                      # follicle definitions / annotation rules
│   ├── labelmap.json                    # class_name → int mapping
│   ├── gold_set/
│   │   └── labeled_tiles.csv            # consolidated labels (validate_exports output)
│   └── raw_exports/                     # QuPath CSV exports consumed by Python
│       ├── annotations_*.csv
│       ├── measurements_*.csv
│       └── ...
│
├── src/                                 # reusable library code
│   ├── ingest/
│   │   └── ingest.py
│   ├── preprocess/
│   │   └── preprocess.py
│   ├── annotate/
│   │   └── join_labels.py
│   ├── train/
│   │   ├── dataset.py
│   │   └── model.py
│   ├── infer/
│   │   └── infer.py
│   ├── postprocess/
│   │   └── count.py
│   └── utils/
│       ├── config.py                    # YAML config loading
│       ├── paths.py                     # repo root resolution
│       ├── logging.py                   # logging + timestamps
│       ├── device.py                    # torch device selection
│       ├── seed.py                      # reproducibility seeds
│       └── io.py                        # CSV read/write helpers
│
├── run/                                 # authoritative Python entrypoints
│   ├── ingest.py                        # download WSIs + build manifest
│   ├── preprocess.py                    # tile WSIs into patches
│   ├── validate_exports.py              # consolidate QuPath annotation exports
│   ├── organize_splits.py              # labeled tiles → train/valid/test folder layout
│   ├── cnn_pipeline.py                  # train ResNet34 + evaluate + WSI inference
│   ├── infer.py                         # standalone re-inference on new tiles
│   └── postprocess_count.py             # aggregate tile predictions → slide counts
│
├── outputs/                             # generated artifacts (gitignored)
│   ├── logs/
│   ├── models/
│   │   └── run_YYYYMMDD_HHMMSS/
│   │       └── best_resnet34.pth
│   ├── predictions/
│   │   ├── test_predictions.csv
│   │   └── slide_level_predictions.csv
│   ├── figures/
│   │   ├── confusion_matrix.png
│   │   ├── roc_curves.png
│   │   └── top_losses.png
│   └── reports/
│
├── EDA/                             # exploratory, non-authoritative analysis
│   ├── 00_dataset_sanity.py
│   ├── 01_view_tiles.py
│   ├── 02_overlay_masks.py
│   ├── 03_annotation_audit.py
│   ├── 04_error_analysis.py
│   ├── 05_make_presentation_figs.py
│   └── archive/                         # superseded reference implementations
│       ├── README.md
│       ├── train_torchvision.py
│       ├── eval_report_standalone.py
│       └── MachineLearningPipeline_v3.py
│
├── tests/                               # smoke tests
│   └── test_config_loading.py
│
└── scripts/                             # Bash orchestration layer
    ├── env.sh                           # shared path + venv helpers
    ├── doctor.sh                        # environment health checks
    ├── setup_env.sh                     # first-time setup
    ├── run_stage.sh                     # reusable logging wrapper
    ├── download_mother_nmr.sh           # MOTHER database downloader
    ├── run_ingest.sh                    # stage 1: ingest
    ├── run_preprocess.sh                # stage 2: preprocess (tiling)
    ├── run_qupath_import.sh             # import images into QuPath project
    ├── run_qupath_export.sh             # run QuPath export scripts
    ├── run_annotate.sh                  # stage 3: validate/consolidate exports
    ├── run_organize_splits.sh           # stage 4: folder layout for training
    ├── run_cnn_pipeline.sh              # stage 5: train + eval (+ WSI inference)
    ├── run_infer.sh                     # standalone re-inference
    ├── run_postprocess_count.sh         # stage 6: slide-level aggregation
    └── run_pipeline.sh                  # full end-to-end orchestration
```

## What Lives Where

- **configs/** — source of truth for stage parameters and paths. Each stage reads its own YAML config; CLI args override when provided.
- **run/** — authoritative Python entrypoints. Each script is a self-contained stage with argparse CLI. The canonical training pipeline is `cnn_pipeline.py` (fastai/ResNet34).
- **src/utils/** — shared helpers (config loading, repo path resolution, CSV I/O, logging, device selection, seeds).
- **scripts/** — Bash orchestration wrappers that handle logging, venv activation, and argument forwarding. Every stage should be run through its wrapper.
- **annotations/ + QuPath/** — human annotation protocol, label map, raw QuPath exports, and Groovy automation scripts.
- **data/** — pipeline data at each processing stage (raw → interim → processed). Gitignored.
- **outputs/** — models, predictions, figures, and logs. Gitignored.
- **explore/** — non-authoritative EDA notebooks and scripts. The `archive/` subfolder holds superseded implementations kept for reference.
- **tests/** — lightweight smoke checks for config loading, path resolution, and split ratios.

## Additional Resources

Please review CONTRIBUTING.md before making changes.

- [Contributing](https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/CONTRIBUTING.md)
- [Git Setup](https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/git_setup.sh)

## AI Disclosure and Acknowledgments

- **Code Development:** Debugging support and logic optimization for the data parsing, image analysis, and model training pipelines were facilitated by ChatGPT (GPT 5.2 Thinking) and Claude (Opus 4.6).
- **Project Architecture:** The repository structure, pipeline streamlining, and high-level workflow diagrams were refined and structured using Claude (Opus 4.6).
