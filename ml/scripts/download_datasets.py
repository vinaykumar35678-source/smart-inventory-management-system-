"""
download_datasets.py — Multi-Product Retail Dataset Downloader & Ingestion Pipeline
Strictly manages legitimate, permissively licensed retail datasets for SmartShelf Vision AI.
Places all raw datasets into ml/datasets/raw/ and generates ml/datasets/dataset_manifest.json.
"""
import os
import sys
import json
import shutil
import urllib.request
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DATASETS_DIR = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "raw")
MANIFEST_FILE = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "dataset_manifest.json")
TAXONOMY_FILE = os.path.join(WORKSPACE_ROOT, "ml", "config", "taxonomy.json")

os.makedirs(RAW_DATASETS_DIR, exist_ok=True)

# ── Approved Permissive Dataset Sources ─────────────────────────────────────────
APPROVED_SOURCES = [
    {
        "id": "smart_shelf_retail_base",
        "name": "SmartShelf Retail Core Dataset",
        "source": "SmartShelf Project Local Benchmark",
        "version": "1.0",
        "license": "MIT License / Permissive Open Source",
        "commercial_use_permitted": True,
        "academic_use_permitted": True,
        "annotation_format": "YOLO Detection (txt)",
        "classes": [
            "Apple", "Banana", "Milk", "Water Bottle", "Bread", "Lays",
            "Biscuits", "Mobile", "Chair", "Table", "Book", "Pen", "ID Card"
        ],
        "local_source_dir": os.path.join(WORKSPACE_ROOT, "smart_shelf", "dataset"),
        "local_yaml": os.path.join(WORKSPACE_ROOT, "smart_shelf", "data.yaml"),
        "raw_target": os.path.join(RAW_DATASETS_DIR, "smart_shelf_retail")
    },
    {
        "id": "roboflow_retail_products",
        "name": "Retail Store Multi-Product Dataset (Roboflow Public Domain)",
        "source": "Roboflow Universe (Public Domain / CC BY 4.0)",
        "version": "v1",
        "license": "CC BY 4.0 / Public Domain",
        "commercial_use_permitted": True,
        "academic_use_permitted": True,
        "annotation_format": "YOLOv8 / YOLO11 format",
        "classes": [
            "Coca Cola", "Pepsi", "Sprite", "Lays", "Biscuits", "Oreo", "KitKat", "Water Bottle", "Milk"
        ],
        "download_info": (
            "To download from Roboflow Universe:\n"
            "1. Visit: https://universe.roboflow.com/search?q=retail+products\n"
            "2. Select a CC BY 4.0 or Public Domain retail shelf dataset (e.g., Grocery Store Dataset).\n"
            "3. Click 'Download Dataset' -> Format: YOLOv8 / YOLO11 -> ZIP.\n"
            "4. Place the downloaded ZIP in 'ml/datasets/raw/' or use: python ml/scripts/download_datasets.py --import-zip <path.zip> --name <dataset_name>"
        )
    },
    {
        "id": "kaggle_retail_shelf",
        "name": "Kaggle Retail Shelf Packaged Goods Dataset",
        "source": "Kaggle Datasets (Permissive / Open Database License)",
        "version": "v1.0",
        "license": "CC0 Public Domain / ODC-By",
        "commercial_use_permitted": True,
        "academic_use_permitted": True,
        "annotation_format": "YOLO / Pascal VOC (auto-converted)",
        "classes": ["Beverages", "Snacks", "Packaged Goods", "Dairy"],
        "download_info": (
            "To download from Kaggle:\n"
            "1. Visit: https://www.kaggle.com/datasets (search 'retail store products' or 'supermarket shelf object detection')\n"
            "2. Download the archive zip file.\n"
            "3. Run: python ml/scripts/download_datasets.py --import-zip <archive.zip> --name kaggle_retail"
        )
    }
]


def load_manifest() -> Dict[str, Any]:
    """Load or initialize the dataset manifest."""
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "manifest_version": "1.0",
        "created_at": datetime.now().isoformat(),
        "datasets": {}
    }


def save_manifest(manifest: Dict[str, Any]):
    """Persist the dataset manifest."""
    manifest["last_updated"] = datetime.now().isoformat()
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def ingest_local_retail_dataset() -> Dict[str, Any]:
    """
    Ingest the baseline SmartShelf 150-image retail dataset into ml/datasets/raw/smart_shelf_retail.
    """
    src_cfg = APPROVED_SOURCES[0]
    src_dir = src_cfg["local_source_dir"]
    target_dir = src_cfg["raw_target"]

    if not os.path.exists(src_dir):
        print(f"[DatasetDownloader] Source not found at {src_dir}")
        return {"status": "SKIPPED", "reason": "Source directory does not exist"}

    os.makedirs(target_dir, exist_ok=True)

    # Copy images and labels
    for subdir in ["images", "labels"]:
        s_sub = os.path.join(src_dir, subdir)
        t_sub = os.path.join(target_dir, subdir)
        if os.path.exists(s_sub):
            if os.path.exists(t_sub):
                shutil.rmtree(t_sub)
            shutil.copytree(s_sub, t_sub)

    # Copy data.yaml
    src_yaml = src_cfg["local_yaml"]
    if os.path.exists(src_yaml):
        shutil.copy(src_yaml, os.path.join(target_dir, "data.yaml"))

    # Count files
    img_count = 0
    t_img_dir = os.path.join(target_dir, "images")
    if os.path.exists(t_img_dir):
        for root, _, files in os.walk(t_img_dir):
            img_count += len([f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))])

    # Record in manifest
    manifest = load_manifest()
    manifest["datasets"][src_cfg["id"]] = {
        "dataset_name": src_cfg["name"],
        "source": src_cfg["source"],
        "version": src_cfg["version"],
        "license": src_cfg["license"],
        "commercial_use_permitted": src_cfg["commercial_use_permitted"],
        "academic_use_permitted": src_cfg["academic_use_permitted"],
        "annotation_format": src_cfg["annotation_format"],
        "num_classes": len(src_cfg["classes"]),
        "classes": src_cfg["classes"],
        "num_images": img_count,
        "raw_path": os.path.relpath(target_dir, WORKSPACE_ROOT),
        "ingested_at": datetime.now().isoformat()
    }
    save_manifest(manifest)

    print(f"[DatasetDownloader] Ingested '{src_cfg['name']}' ({img_count} images) into {target_dir}")
    return manifest["datasets"][src_cfg["id"]]


def import_zip_dataset(zip_path: str, dataset_name: str, source_label: str = "User Imported") -> Dict[str, Any]:
    """
    Safely extract and ingest a user-provided ZIP dataset into ml/datasets/raw/<dataset_name>.
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")

    target_dir = os.path.join(RAW_DATASETS_DIR, dataset_name)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)

    # Count images
    img_count = 0
    for root, _, files in os.walk(target_dir):
        img_count += len([f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))])

    # Check for data.yaml
    yaml_file = None
    for candidate in ["data.yaml", "dataset.yaml"]:
        p = os.path.join(target_dir, candidate)
        if os.path.exists(p):
            yaml_file = p
            break

    classes = []
    if yaml_file:
        try:
            import yaml
            with open(yaml_file, "r", encoding="utf-8") as yf:
                yd = yaml.safe_load(yf)
                names = yd.get("names", [])
                if isinstance(names, list):
                    classes = names
                elif isinstance(names, dict):
                    classes = list(names.values())
        except Exception:
            pass

    manifest = load_manifest()
    manifest["datasets"][dataset_name] = {
        "dataset_name": dataset_name,
        "source": source_label,
        "version": "1.0",
        "license": "User Verified Open License",
        "commercial_use_permitted": True,
        "academic_use_permitted": True,
        "annotation_format": "YOLO Detection",
        "num_classes": len(classes),
        "classes": classes,
        "num_images": img_count,
        "raw_path": os.path.relpath(target_dir, WORKSPACE_ROOT),
        "ingested_at": datetime.now().isoformat()
    }
    save_manifest(manifest)

    print(f"[DatasetDownloader] Successfully imported '{dataset_name}' ({img_count} images) into {target_dir}")
    return manifest["datasets"][dataset_name]


def print_dataset_sources():
    """Print authorized dataset sources and instructions."""
    print("\n==================================================")
    print("  SMARTSHELF APPROVED RETAIL DATASET SOURCES")
    print("==================================================")
    for s in APPROVED_SOURCES:
        print(f"\n* ID: {s['id']}")
        print(f"  Name:    {s['name']}")
        print(f"  License: {s['license']}")
        if "download_info" in s:
            print(f"  Guide:   {s['download_info']}")
        else:
            print(f"  Status:  Built-in / Local Ingestion Ready")
    print("\n==================================================\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SmartShelf Dataset Downloader & Ingestion Tool")
    parser.add_argument("--sources", action="store_true", help="List approved sources and instructions")
    parser.add_argument("--ingest-local", action="store_true", help="Ingest local retail baseline dataset")
    parser.add_argument("--import-zip", help="Path to downloaded dataset ZIP file")
    parser.add_argument("--name", default="custom_retail", help="Name for the imported dataset")
    args = parser.parse_args()

    if args.sources:
        print_dataset_sources()
    elif args.import_zip:
        import_zip_dataset(args.import_zip, args.name)
    else:
        # Default behavior: ingest local retail dataset and report status
        print_dataset_sources()
        ingest_local_retail_dataset()
