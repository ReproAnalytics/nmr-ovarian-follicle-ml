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
bash getting_started.sh

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
├── README.md
├── CONTRIBUTING.md
├── getting_started.sh
├── git_setup.sh
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
│   ├── raw/H-glaber            # OME-TIFF slides and XML metadata
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
├── run/                         # PRIMARY Python execution entrypoints
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
└── 
   
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
