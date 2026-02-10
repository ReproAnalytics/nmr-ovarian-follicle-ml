# README

This project develops a machine-learning pipeline for automated identification, segmentation, and quantification of ovarian follicles in histological images of naked mole rats. Utilizing data from the MOTHER repository, the pipeline adapts and evaluates existing follicle-detection algorithms to address the unique morphological characteristics of naked mole rat ovarian tissue.

## Getting Started

Please read the following guides before starting the project:

- Getting Started <https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/getting_started.sh>

- Contributing <https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/CONTRIBUTING.md>

## Repo Structure

```text
nmr-ovarian-follicle-ml/
├── README.md
├── CONTRIBUTING.md
├── getting_started.sh
├── scaffold_project.sh
├── .gitignore
│
├── environment/
│   └── requirements.txt
│
├── configs/
│   ├── dataset.yaml             # dataset paths, species, split ratios
│   ├── preprocess.yaml          # tiling and normalization parameters
│   ├── train.yaml               # model architecture and training settings
│   ├── infer.yaml               # inference thresholds and batching
│   └── eval.yaml                # evaluation metrics and reporting options
│
├── data/                        # gitignored (raw and intermediate data)
│   ├── raw/                     # OME-TIFF slides and XML metadata
│   ├── interim/                 # tiled/normalized images
│   └── processed/               # ML-ready tensors and masks
│
├── annotations/
│   ├── protocol.md              # annotation guidelines (QuPath workflow)
│   ├── labelmap.json            # follicle class definitions
│   └── gold_set/                # curated ground-truth annotations
│
├── outputs/                     # gitignored (generated artifacts)
│   ├── logs/                    # shell-run logs
│   ├── models/                  # trained model checkpoints
│   ├── predictions/             # segmentation outputs
│   ├── metrics/                 # evaluation metrics (CSV/JSON)
│   ├── figures/                 # plots and visualizations
│   └── reports/                 # tables and final summaries
│
├── src/                         # reusable ML code (NO direct execution)
│   ├── ingest/
│   │   └── ingest.py
│   ├── preprocess/
│   │   └── preprocess.py
│   ├── train/
│   │   └── train.py
│   ├── infer/
│   │   └── infer.py
│   ├── postprocess/
│   │   └── count.py
│   ├── eval/
│   │   └── evaluate.py
│   └── utils/
│       ├── config.py            # YAML loading and validation
│       ├── paths.py             # standardized path resolution
│       ├── logging.py           # logging utilities
│       ├── seed.py              # reproducibility helpers
│       └── io.py                # I/O and manifest utilities
│
├── run/                         # PRIMARY execution interface (Python)
│   ├── ingest.py                # calls src/ingest/*
│   ├── preprocess.py            # calls src/preprocess/*
│   ├── train.py                 # calls src/preprocess/*
│   ├── infer.py                 # calls src/infer/*
│   ├── postprocess_count.py     # calls src/postprocess/*
│   └── eval_report.py           # calls src/eval/*
│
├── explore/                     # exploration & visualization (non-authoritative)
│   ├── 00_dataset_sanity.py
│   ├── 01_view_tiles.py
│   ├── 02_overlay_masks.py
│   ├── 03_annotation_audit.py
│   ├── 04_error_analysis.py
│   └── 05_make_presentation_figs.py
│
├── scripts/                     # OPTIONAL shell orchestration 
│   ├── env.sh                   # shared helpers (paths, venv, defaults)
│   ├── doctor.sh                # environment + file sanity checks
│   ├── run_stage.sh             # standardized logging wrapper → outputs/logs/
│   ├── setup_env.sh             # one-time environment setup
│   ├── run_ingest.sh            # calls run/ingest.py with configs/dataset.yaml
│   ├── run_preprocess.sh        # calls run/preprocess.py with configs/preprocess.yaml
│   ├── run_train.sh             # calls run/train.py with configs/train.yaml
│   ├── run_infer.sh             # calls run/infer.py with configs/infer.yaml
│   ├── run_postprocess_count.sh # calls run/postprocess_count.py
│   ├── run_eval_report.sh       # calls run/eval_report.py with configs/eval.yaml
│   └── run_pipeline.sh          # runs stages in order (end-to-end orchestration)
│
└── tests/
    └── test_config_loading.py
```

**Note:**

- All official pipeline execution occurs via run/*.py scripts.

- Shell scripts in scripts/ are optional orchestration helpers.

- Notebooks are not used; exploratory analysis is performed using .py scripts in explore/
