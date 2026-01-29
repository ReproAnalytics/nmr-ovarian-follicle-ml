# README

This project develops a machine-learning pipeline for the automated identification, segmentation, and quantification of ovarian follicles in naked mole rat histological images. Utilizing data from the MOTHER repository, the pipeline adapts and evaluates existing follicle-detection algorithms to address the unique morphological characteristics of naked mole rat ovarian tissue.

## Getting Started

Please read the 'Getting Started' guide before starting the project.

## Repo Structure

nmr-ovarian-follicle-ml/
├── README.md
├── .gitignore
│
├── environment/
│   └── requirements.txt
│
├── configs/
│   ├── dataset.yaml
│   ├── preprocess.yaml
│   ├── train.yaml
│   ├── infer.yaml
│   └── eval.yaml
│
├── data/                           # gitignored
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── annotations/
│   ├── protocol.md
│   ├── labelmap.json
│   └── gold_set/
│
├── outputs/                        # gitignored
│   ├── logs/                       # NEW: shell-run logs (Option A)
│   ├── models/
│   ├── predictions/
│   ├── metrics/
│   ├── figures/
│   └── reports/
│
├── src/                            # reusable ML code (NO execution)
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
│       ├── config.py
│       ├── paths.py
│       ├── logging.py
│       ├── seed.py
│       └── io.py
│
├── run/                            # PRIMARY execution interface (Python)
│   ├── ingest.py
│   ├── preprocess.py
│   ├── train.py
│   ├── infer.py
│   ├── postprocess_count.py
│   └── eval_report.py
│
├── explore/                        # exploration (no training/infer as source of truth)
│   ├── 00_dataset_sanity.py
│   ├── 01_view_tiles.py
│   ├── 02_overlay_masks.py
│   ├── 03_annotation_audit.py
│   ├── 04_error_analysis.py
│   └── 05_make_presentation_figs.py
│
├── scripts/                        # OPTIONAL shell orchestration (Option A upgraded)
│   ├── env.sh                      # NEW: shared helpers (paths, venv, defaults)
│   ├── doctor.sh                   # NEW: preflight checks
│   ├── run_stage.sh                # NEW: consistent logging wrapper
│   ├── setup_env.sh                # one-time environment helper
│   ├── run_ingest.sh
│   ├── run_preprocess.sh
│   ├── run_train.sh
│   ├── run_infer.sh
│   ├── run_postprocess_count.sh
│   ├── run_eval_report.sh
│   └── run_pipeline.sh             # end-to-end (calls doctor + run_stage)
│
└── tests/
    └── test_config_loading.py
