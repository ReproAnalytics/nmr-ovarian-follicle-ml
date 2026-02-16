# README

This project develops a machine-learning pipeline for automated identification, segmentation, and quantification of ovarian follicles in histological images of naked mole rats.
The pipeline uses data from the MOTHER repository <https://mother-db.org/> and evaluates follicle-detection algorithms to address the unique morphological characteristics of naked mole rat ovarian tissue.

The repository is designed for **reproducible, team-based research**, with a clear separation between reusable library code, executable pipeline stages, configuration files, and generated outputs.

## Quickstart

This project is designed so **everyone runs the same commands**.  
You do **not** need to call Python files directly.

### Prerequisites

- Python 3.10+ available as `python`
- WSL/Linux/macOS

### One-time setup (or when environment breaks)

```bash
# Clone the ReproAnalytics repo
git clone git@github.com:ReproAnalytics/nmr-ovarian-follicle-ml.git
cd nmr-ovarian-follicle-ml

# Run setup (creates venv, installs dependencies, verifies environment)
bash scripts/setup_env.sh

# Check environment health
bash scripts/doctor.sh
```

This will:

- clone the nmr-ovarian-follicle-ml repo
- create a local virtual environment (.venv)
- install all Python dependencies
- verify your setup
- print the next recommended steps


## Run Pipeline

```bash
# Run the full pipeline
bash scripts/run_pipeline.sh

# Or run individual stages
bash scripts/run_ingest.sh
bash scripts/run_preprocess.sh
bash scripts/run_train.sh
bash scripts/run_infer.sh
bash scripts/run_postprocess_count.sh
bash scripts/run_eval_report.sh
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
│   ├── requirements-dev.txt
│   └── setup_env.sh
│
├── configs/                             # ALL experiment control lives here
│   ├── dataset.yaml                     # ingest + raw data config
│   ├── preprocess.yaml                  # tiling + normalization settings
│   ├── annotate.yaml                    # label joining rules
│   ├── train.yaml                       # model + hyperparameters
│   ├── infer.yaml                       # inference configuration
│   ├── postprocess.yaml                 # follicle counting logic
│   └── eval.yaml                        # evaluation metrics configuration
│
├── data/                                # NEVER committed (gitignored)
│   ├── raw/
│   │   └── H_glaber/
│   │       ├── <accession_id>/
│   │       │   ├── *.ome.tif(f)
│   │       │   ├── *.xml
│   │       │   └── ...
│   │       └── manifest_raw.csv
│   │
│   ├── interim/
│   │   ├── tiles/
│   │   │   └── H_glaber/
│   │   │       └── <accession_id>/
│   │   │           ├── tile_x_y.png
│   │   │           └── ...
│   │   └── tiles_manifest.csv
│   │
│   └── processed/
│       ├── train_split.csv
│       ├── val_split.csv
│       └── test_split.csv
│
├── annotations/                         # human supervision layer
│   ├── protocol.md                      # follicle definitions
│   ├── labelmap.json                    # class_name -> int
│   ├── gold_set/
│   │   └── labeled_tiles.csv
│   └── raw_exports/                     # QuPath/CVAT exports
│
├── outputs/                             # all model artifacts (gitignored)
│   ├── models/
│   │   ├── run_YYYYMMDD_HHMM/
│   │   │   ├── model.pt
│   │   │   └── config_snapshot.yaml
│   │   └── latest.pt
│   │
│   ├── predictions/
│   │   ├── tiles_predictions.csv
│   │   └── slide_level_predictions.csv
│   │
│   ├── metrics/
│   │   ├── run_YYYYMMDD_HHMM.json
│   │   └── tiles_metrics.json
│   │
│   ├── figures/
│   │   ├── confusion_matrix.png
│   │   ├── class_distribution.png
│   │   └── error_examples/
│   │
│   └── reports/
│       └── evaluation_report.md
│
├── src/                                 # PURE ML ENGINE (no side effects)
│   ├── ingest/
│   │   └── ingest.py
│   │
│   ├── preprocess/
│   │   └── preprocess.py
│   │
│   ├── annotate/
│   │   └── join_labels.py
│   │
│   ├── train/
│   │   ├── dataset.py
│   │   ├── model.py
│   │   └── train.py
│   │
│   ├── infer/
│   │   └── infer.py
│   │
│   ├── postprocess/
│   │   └── count.py
│   │
│   ├── eval/
│   │   └── evaluate.py
│   │
│   └── utils/
│       ├── config.py                    # YAML loading + validation
│       ├── paths.py                     # repo root resolution
│       ├── logging.py                   # structured logging
│       ├── seed.py                      # reproducibility helpers
│       └── io.py                        # manifest + file utilities
│
├── run/                                 # AUTHORITATIVE PYTHON ENTRYPOINTS
│   ├── ingest.py
│   ├── preprocess.py
│   ├── annotate.py
│   ├── train.py
│   ├── infer.py
│   ├── postprocess_count.py
│   └── eval_report.py
│
├── explore/                             # non-authoritative research tools
│   ├── 00_dataset_sanity.py
│   ├── 01_view_tiles.py
│   ├── 02_overlay_masks.py
│   ├── 03_annotation_audit.py
│   ├── 04_error_analysis.py
│   └── 05_make_presentation_figs.py
│
└── scripts/                             # OPTIONAL orchestration layer
    ├── env.sh                           # shared path + venv helpers
    ├── doctor.sh                        # environment checks
    ├── run_stage.sh                     # logging wrapper
    ├── setup_env.sh                     # first-time setup
    ├── run_ingest.sh
    ├── run_preprocess.sh
    ├── run_annotate.sh
    ├── run_train.sh
    ├── run_infer.sh
    ├── run_postprocess.sh
    ├── run_eval_report.sh
    └── run_pipeline.sh                  # full end-to-end execution

   
```

## Execution Model

- All official pipeline execution should be done via **scripts/*.sh**
- **run/*.py** files are the canonical Python entrypoints, but are not run directly unless while developing
- **src/** contains reusable library code and should never be executed directly
- All parameters are controlled through **configs/*.yaml**
- Notebooks are not used; exploratory analysis is performed using .py scripts in explore/

### Additional Resources

Please review CONTRIBUTING.md before making changes.

- Contributing <https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/CONTRIBUTING.md>
- Git Setup <https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/git_setup.sh>
