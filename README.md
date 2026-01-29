# README

This project develops a machine-learning pipeline for automated identification, segmentation, and quantification of ovarian follicles in histological images of naked mole rats. Utilizing data from the MOTHER repository, the pipeline adapts and evaluates existing follicle-detection algorithms to address the unique morphological characteristics of naked mole rat ovarian tissue.

## Getting Started

Please read the 'Getting Started' guide before starting the project: <https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/

## Repo Structure

```text
nmr-ovarian-follicle-ml/
├── README.md
├── CONTRIBUTING.md
├── getting_started.sh
├── .gitignore
│
├── environment/
│   └── requirements.txt
│
├── configs/
│   ├── dataset.yaml            # dataset paths, species, split ratios
│   ├── preprocess.yaml         # tiling and normalization parameters
│   ├── train.yaml              # model architecture and training settings
│   ├── infer.yaml              # inference thresholds and batching
│   └── eval.yaml               # evaluation metrics and reporting options
│
├── data/                       # gitignored (raw and intermediate data)
│   ├── raw/                    # OME-TIFF slides and XML metadata
│   ├── interim/                # tiled/normalized images
│   └── processed/              # ML-ready tensors and masks
│
├── annotations/
│   ├── protocol.md             # annotation guidelines (QuPath workflow)
│   ├── labelmap.json           # follicle class definitions
│   └── gold_set/               # curated ground-truth annotations
│
├── outputs/                    # gitignored (generated artifacts)
│   ├── logs/                   # shell-run logs
│   ├── models/                 # trained model checkpoints
│   ├── predictions/            # segmentation outputs
│   ├── metrics/                # evaluation metrics (CSV/JSON)
│   ├── figures/                # plots and visualizations
│   └── reports/                # tables and final summaries
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
│       ├── config.py           # YAML loading and validation
│       ├── paths.py            # standardized path resolution
│       ├── logging.py          # logging utilities
│       ├── seed.py             # reproducibility helpers
│       └── io.py               # I/O and manifest utilities
│
├── run/                         # PRIMARY execution interface (Python)
│   ├── ingest.py
│   ├── preprocess.py
│   ├── train.py
│   ├── infer.py
│   ├── postprocess_count.py
│   └── eval_report.py
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
│   ├── doctor.sh                # prelim environment checks
│   ├── run_stage.sh             # standardized logging wrapper
│   ├── setup_env.sh             # one-time environment setup
│   ├── run_ingest.sh
│   ├── run_preprocess.sh
│   ├── run_train.sh
│   ├── run_infer.sh
│   ├── run_postprocess_count.sh
│   ├── run_eval_report.sh
│   └── run_pipeline.sh          # end-to-end orchestration
│
└── tests/
    └── test_config_loading.py
```

**Note:**

- All official pipeline execution occurs via run/*.py scripts.

- Shell scripts in scripts/ are optional orchestration helpers.

- Notebooks are not used; exploratory analysis is performed using .py scripts in explore/.
