# README

This project develops a machine-learning pipeline for automated identification, segmentation, and quantification of ovarian follicles in histological images of naked mole rats.
The pipeline uses data from the MOTHER repository <https://mother-db.org/> and evaluates follicle-detection algorithms to address the unique morphological characteristics of naked mole rat ovarian tissue.

The repository is designed for **reproducible, team-based research**, with a clear separation between reusable library code, executable pipeline stages, configuration files, and generated outputs.

## Quickstart

This project is designed so that **everyone runs the same commands**.  
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

# EDA
source .venv/bin/activate
python explore/00_dataset_sanity.py --raw-root data/raw/H_glaber
python explore/01_view_tiles.py
```

## Data Pipeline Flow

1. Bash ingests WSI images and XML metadata
2. Bash preprocess data
3. Bash launches QuPath import stage
4. QuPath project created/updated in repo_home/QuPath/project
5. OME-TIFF images imported from repo_home/data/raw/H_glaber
6. Manual annotation in QuPath GUI
7. Bash runs QuPath export scripts
8. Python validates/normalizes exports for training
9. Python performs model training


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
│   ├── train.yaml                       # model + hyperparameters
│   ├── infer.yaml                       # inference configuration
│   ├── postprocess.yaml                 # follicle counting logic
│   └── eval.yaml                        # evaluation metrics configuration
│
├── data/                                # pipeline data states (gitignored)
│   ├── raw/                             # Bash ingest writes here
│   │   └── H_glaber/
│   │       ├── <accession_id>/
│   │       │   ├── *.ome.tif(f)
│   │       │   ├── *.xml
│   │       │   └── ...
│   │       └── manifest_raw.csv
│   │
│   ├── interim/                         # Bash/Python preprocess writes here
│   │   ├── tiles/
│   │   │   └── H_glaber/
│   │   │       └── <accession_id>/
│   │   │           ├── tile_x_y.png
│   │   │           └── ...
│   │   └── tiles_manifest.csv
│   │
│   └── processed/                       # Python training-ready datasets
│       ├── train_split.csv
│       ├── val_split.csv
│       └── test_split.csv
│
├── QuPath/                              # QuPath stage lives inside repo
│   ├── project/                         # created/updated by Bash launcher
│   └── scripts/
│       ├── import_images.groovy         # import OME-TIFF from data/raw/H_glaber
│       ├── export_annotations.groovy    # export annotations back to repo
│       └── export_measurements.groovy   # export measurements back to repo
│
├── annotations/                         # human supervision layer
│   ├── protocol.md                      # follicle definitions / annotation rules
│   ├── labelmap.json                    # class_name -> int
│   ├── gold_set/
│   │   └── labeled_tiles.csv
│   └── raw_exports/                     # QuPath exports consumed by Python
│       ├── annotations_*.csv
│       ├── measurements_*.csv
│       └── ...
│
├── src/                                 # reusable implementation code only
│   ├── ingest/
│   │   └── ingest.py
│   │
│   ├── preprocess/
│   │   └── preprocess.py
│   │
│   ├── annotate/
│   │   └── join_labels.py               # validate/normalize QuPath exports
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
│       ├── config.py
│       ├── paths.py
│       ├── logging.py
│       ├── seed.py
│       └── io.py
│
├── run/                                 # authoritative Python stage entrypoints
│   ├── ingest.py
│   ├── preprocess.py
│   ├── train.py
│   ├── infer.py
│   ├── postprocess_count.py
│   └── eval_report.py
│
├── outputs/                             # generated artifacts (gitignored)
│   ├── logs/
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
├── EDA/                                 # exploratory, non-authoritative analysis
│   ├── 00_dataset_sanity.py
│   ├── 01_view_tiles.py
│   ├── 02_overlay_masks.py
│   ├── 03_annotation_audit.py
│   ├── 04_error_analysis.py
│   ├── 05_make_presentation_figs.py
│   └── eda_appendix.md
│
└── scripts/                             # Bash orchestration layer
    ├── env.sh                           # shared path + venv helpers
    ├── doctor.sh                        # environment checks
    ├── run_stage.sh                     # logging wrapper
    ├── setup_env.sh                     # first-time setup
    ├── run_ingest.sh                    # Bash ingests WSI + XML
    ├── run_preprocess.sh                # Bash preprocess stage
    ├── run_qupath_project.sh            # launch/update QuPath project and import images
    ├── run_qupath_export.sh             # run QuPath export scripts
    ├── run_train.sh                     # Python model training
    ├── run_infer.sh
    ├── run_postprocess.sh
    ├── run_eval_report.sh
    └── run_pipeline.sh                  # full end-to-end orchestration

```

## Execution Model

- All official pipeline execution should be done via **scripts/*.sh**
- **run/*.py** files are the canonical Python entrypoints, but are not run directly while developing
- **src/** contains reusable library code and should never be executed directly
- All parameters are controlled through **configs/*.yaml**
- Notebooks are not used; exploratory analysis is performed using .py scripts in EDA/

### Additional Resources

Please review CONTRIBUTING.md before making changes.

- Contributing <https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/CONTRIBUTING.md>
- Git Setup <https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/git_setup.sh>

### AI Disclosure and Acknowledgments

- Code Development: Debugging support and logic optimization for the data parsing, image analysis, and model training pipelines were facilitated by ChatGPT (GPT 5.2 Thinking).
- Project Architecture: The repository structure and high-level project workflow diagrams were refined and structured using Claude 4.6 Sonnet (Extended).
