"""
download_kaggle_dataset.py — Automated Kaggle Retail Dataset Downloader & YOLO Prep
Usage:
  1. Place your kaggle.json in ~/.kaggle/ (or C:\\Users\\<username>\\.kaggle\\kaggle.json)
  2. Run: python download_kaggle_dataset.py --dataset "gpiosenka/grocery-store-dataset"
"""
import os
import argparse
import zipfile

def download_and_extract_kaggle_dataset(dataset_slug: str, output_dir: str = "./dataset"):
    """
    Downloads a Kaggle dataset using kaggle API and extracts it to dataset folder.
    """
    try:
        import kaggle
    except ImportError:
        print("[INFO] Installing Kaggle API library...")
        os.system("pip install kaggle")
        import kaggle

    os.makedirs(output_dir, exist_ok=True)
    print(f"[INFO] Downloading Kaggle dataset: {dataset_slug}...")
    
    # Download dataset zip
    kaggle.api.dataset_download_files(dataset_slug, path=output_dir, unzip=True)
    print(f"[SUCCESS] Dataset extracted to {os.path.abspath(output_dir)}")
    print("[NEXT STEP] Update data.yaml with your dataset class names and run: python train.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and prepare Kaggle dataset for YOLO11")
    parser.add_argument("--dataset", type=str, default="sku110k-dataset", help="Kaggle dataset slug (e.g. gpiosenka/grocery-store-dataset)")
    args = parser.parse_args()
    
    download_and_extract_kaggle_dataset(args.dataset)
