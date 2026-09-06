# SmartShelf Vision AI — Multi-Product Retail Datasets

This directory houses retail store and grocery shelf datasets used to train custom YOLO11 models for multi-product inventory identification and ByteTrack spatial tracking.

---

## Directory Architecture

```
ml/datasets/
├── raw/                 # Downloaded or imported raw datasets (git-ignored)
│   └── <dataset_name>/  # e.g., smart_shelf_retail, roboflow_retail
│       ├── images/
│       ├── labels/
│       └── data.yaml
├── processed/           # Standardized YOLO annotations per source (git-ignored)
├── merged/              # Final consolidated multi-product dataset (git-ignored)
│   ├── images/          # train/ (70%), val/ (20%), test/ (10%)
│   ├── labels/          # train/, val/, test/
│   └── data.yaml        # Auto-generated dataset configuration
├── validation/          # Intermediate verification artifacts (git-ignored)
├── dataset_manifest.json# Complete provenance and licensing records
├── dataset_report.html  # Interactive visual audit and bounding box report
└── README.md            # Sourcing and preparation documentation
```

---

## Approved Dataset Sources & Licenses

| Source / Dataset Name | License | Allowed Use | Classes | Format |
| :--- | :--- | :--- | :--- | :--- |
| **SmartShelf Retail Core** | MIT / Permissive Open Source | Academic & Commercial | 13 Retail Items | YOLO (txt) |
| **Roboflow Retail Products** | CC BY 4.0 / Public Domain | Academic & Commercial | Multi-Product Retail | YOLOv8/11 |
| **Kaggle Retail Packaged Goods** | CC0 Public Domain / ODC-By | Academic & Commercial | Supermarket Shelf | YOLO / VOC |

> [!IMPORTANT]
> Raw dataset images are excluded from Git to prevent repository bloat and comply with repository size guidelines. Datasets are downloaded or ingested locally using the provided automation scripts.

---

## How to Obtain & Ingest Datasets

### Option A: Automatic Built-in Ingestion (Recommended)
Run the automated downloader to ingest the baseline retail dataset:
```bash
python ml/scripts/download_datasets.py
```
This populates `ml/datasets/raw/smart_shelf_retail` and updates `ml/datasets/dataset_manifest.json`.

### Option B: Download from Roboflow Universe
1. Visit [Roboflow Universe — Retail Products](https://universe.roboflow.com/search?q=retail+products).
2. Filter by **CC BY 4.0** or **Public Domain** licenses.
3. Export the dataset as **YOLOv8** format ZIP.
4. Import into the system:
   ```bash
   python ml/scripts/download_datasets.py --import-zip path/to/dataset.zip --name roboflow_retail
   ```

### Option C: Download from Kaggle
1. Download a permissive retail shelf dataset (e.g., supermarket shelf detection).
2. Import the archive:
   ```bash
   python ml/scripts/download_datasets.py --import-zip path/to/kaggle_archive.zip --name kaggle_retail
   ```

---

## Dataset Normalization & Preparation

To normalize annotations, eliminate duplicates, apply the canonical taxonomy (`ml/config/taxonomy.json`), and generate a 70% Train / 20% Val / 10% Test split:

```bash
python ml/scripts/prepare_dataset.py
```

This generates `ml/datasets/merged/data.yaml` and places images and labels into `ml/datasets/merged/images/` and `ml/datasets/merged/labels/`.

---

## Dataset Quality & Integrity Validation

To run comprehensive bounding box geometry checks, detect corrupted images, check coordinate ranges `[0.0, 1.0]`, and generate the visual audit report:

```bash
python ml/scripts/validate_dataset.py
```

This generates `ml/datasets/dataset_report.html`, which can be opened in any web browser to view bounding box previews, class distributions, and balance indicators.
