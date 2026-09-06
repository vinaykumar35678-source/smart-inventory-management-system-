"""
dataset_manager.py — Dataset Import, Auto-Parsing, Validation, and Preview Utility
Supports local folders, ZIP files, and existing project directories.
Auto-detects data.yaml, validates YOLO annotations, and produces visual previews.
"""
import os
import shutil
import zipfile
import yaml
import cv2
import base64
import hashlib
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASETS_DIR = os.path.join(WORKSPACE_ROOT, "ml", "datasets")

os.makedirs(DATASETS_DIR, exist_ok=True)

class DatasetManager:
    def __init__(self, base_dir: str = DATASETS_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all datasets available in ml/datasets and existing project directories."""
        datasets = []
        # 1. Datasets in ml/datasets/
        if os.path.exists(self.base_dir):
            for name in os.listdir(self.base_dir):
                d_path = os.path.join(self.base_dir, name)
                if os.path.isdir(d_path):
                    yaml_path = self._find_yaml(d_path)
                    meta = self.get_dataset_info(d_path, yaml_path)
                    meta["id"] = name
                    meta["path"] = d_path
                    meta["is_custom"] = True
                    datasets.append(meta)

        # 2. Check smart_shelf/dataset
        smart_shelf_ds = os.path.join(WORKSPACE_ROOT, "smart_shelf", "dataset")
        if os.path.exists(smart_shelf_ds):
            yaml_path = os.path.join(WORKSPACE_ROOT, "smart_shelf", "data.yaml")
            meta = self.get_dataset_info(smart_shelf_ds, yaml_path if os.path.exists(yaml_path) else None)
            meta["id"] = "smart_shelf_default"
            meta["name"] = "Smart Shelf Default Dataset (150 Images)"
            meta["path"] = smart_shelf_ds
            meta["is_custom"] = False
            datasets.append(meta)

        # 3. Check root dataset/
        root_ds = os.path.join(WORKSPACE_ROOT, "dataset")
        if os.path.exists(root_ds) and root_ds != self.base_dir:
            yaml_path = os.path.join(WORKSPACE_ROOT, "data.yaml")
            meta = self.get_dataset_info(root_ds, yaml_path if os.path.exists(yaml_path) else None)
            meta["id"] = "root_dataset"
            meta["name"] = "Root Dataset"
            meta["path"] = root_ds
            meta["is_custom"] = False
            datasets.append(meta)

        return datasets

    def import_from_directory(self, source_dir: str, dataset_name: str) -> Dict[str, Any]:
        """Copy a dataset from a local directory into ml/datasets/."""
        if not os.path.exists(source_dir):
            raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

        target_dir = os.path.join(self.base_dir, dataset_name)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        shutil.copytree(source_dir, target_dir)

        # Copy data.yaml if it exists alongside the folder
        parent_yaml = os.path.join(os.path.dirname(source_dir), "data.yaml")
        target_yaml = os.path.join(target_dir, "data.yaml")
        if not os.path.exists(target_yaml) and os.path.exists(parent_yaml):
            shutil.copy(parent_yaml, target_yaml)

        yaml_path = self._find_yaml(target_dir)
        return self.get_dataset_info(target_dir, yaml_path)

    def import_from_zip(self, zip_path: str, dataset_name: str) -> Dict[str, Any]:
        """Extract a ZIP file containing a YOLO dataset into ml/datasets/."""
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP file does not exist: {zip_path}")

        target_dir = os.path.join(self.base_dir, dataset_name)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(target_dir)

        yaml_path = self._find_yaml(target_dir)
        return self.get_dataset_info(target_dir, yaml_path)

    def _find_yaml(self, dir_path: str) -> Optional[str]:
        """Find data.yaml in the dataset folder or one level up."""
        for candidate in ["data.yaml", "dataset.yaml"]:
            p = os.path.join(dir_path, candidate)
            if os.path.exists(p):
                return p
        parent_yaml = os.path.join(os.path.dirname(dir_path), "data.yaml")
        if os.path.exists(parent_yaml):
            return parent_yaml
        return None

    def get_dataset_info(self, dir_path: str, yaml_path: Optional[str] = None) -> Dict[str, Any]:
        """Read data.yaml and count files across train, val, and test."""
        info = {
            "name": os.path.basename(dir_path),
            "path": dir_path,
            "yaml_path": yaml_path,
            "classes": {},
            "num_classes": 0,
            "counts": {"train": 0, "val": 0, "test": 0, "total": 0}
        }

        if yaml_path and os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    yd = yaml.safe_load(f)
                    names = yd.get("names", {})
                    if isinstance(names, list):
                        info["classes"] = {i: n for i, n in enumerate(names)}
                    elif isinstance(names, dict):
                        info["classes"] = {int(k): str(v) for k, v in names.items()}
                    info["num_classes"] = yd.get("nc", len(info["classes"]))
            except Exception as e:
                print(f"[DatasetManager] YAML parse warning: {e}")

        # Count images in splits
        img_dir = os.path.join(dir_path, "images")
        if os.path.exists(img_dir):
            for split in ["train", "val", "test"]:
                sp_dir = os.path.join(img_dir, split)
                if os.path.exists(sp_dir):
                    imgs = [f for f in os.listdir(sp_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]
                    info["counts"][split] = len(imgs)
        else:
            # Maybe flat directory
            imgs = [f for f in os.listdir(dir_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]
            info["counts"]["train"] = len(imgs)

        info["counts"]["total"] = sum(info["counts"].values())
        return info

    def validate_dataset(self, dataset_path: str, yaml_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate YOLO dataset structure, images, annotations, and compute class distribution.
        Detects:
          - Missing images
          - Missing labels
          - Corrupted images
          - Invalid bounding box coordinates
          - Incorrect class IDs
          - Empty labels
          - Duplicate files
        """
        report = {
            "is_valid": True,
            "summary": {
                "total_images": 0,
                "total_labels": 0,
                "valid_annotations": 0,
                "classes_detected": 0
            },
            "issues": {
                "missing_labels": [],
                "missing_images": [],
                "corrupted_images": [],
                "invalid_annotations": [],
                "empty_labels": [],
                "incorrect_class_ids": [],
                "duplicate_files": []
            },
            "class_distribution": {},
            "split_stats": {}
        }

        # Auto-detect YAML if not passed
        if not yaml_path:
            yaml_path = self._find_yaml(dataset_path)

        declared_classes = {}
        if yaml_path and os.path.exists(yaml_path):
            with open(yaml_path, "r", encoding="utf-8") as f:
                yd = yaml.safe_load(f)
                names = yd.get("names", {})
                if isinstance(names, list):
                    declared_classes = {i: n for i, n in enumerate(names)}
                elif isinstance(names, dict):
                    declared_classes = {int(k): str(v) for k, v in names.items()}

        splits = ["train", "val", "test"]
        img_dir = os.path.join(dataset_path, "images")
        lbl_dir = os.path.join(dataset_path, "labels")

        # Fallback if no images/ subdirectory
        if not os.path.exists(img_dir):
            splits = [""]

        file_hashes = {}

        for split in splits:
            s_img_dir = os.path.join(img_dir, split) if split else dataset_path
            s_lbl_dir = os.path.join(lbl_dir, split) if split else os.path.join(dataset_path, "labels")

            if not os.path.exists(s_img_dir):
                continue

            img_files = [f for f in os.listdir(s_img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]
            lbl_files = [f for f in os.listdir(s_lbl_dir) if f.endswith('.txt')] if os.path.exists(s_lbl_dir) else []

            split_name = split if split else "root"
            report["split_stats"][split_name] = {
                "images": len(img_files),
                "labels": len(lbl_files)
            }
            report["summary"]["total_images"] += len(img_files)
            report["summary"]["total_labels"] += len(lbl_files)

            lbl_stem_set = {os.path.splitext(f)[0] for f in lbl_files}
            img_stem_set = {os.path.splitext(f)[0] for f in img_files}

            # Check 1: Missing labels
            for f in img_files:
                stem = os.path.splitext(f)[0]
                if stem not in lbl_stem_set:
                    report["issues"]["missing_labels"].append(f"{split_name}/{f}")

            # Check 2: Missing images
            for f in lbl_files:
                stem = os.path.splitext(f)[0]
                if stem not in img_stem_set:
                    report["issues"]["missing_images"].append(f"{split_name}/{f}")

            # Check 3: Corrupted images & duplicate hash check
            for img_file in img_files:
                img_path = os.path.join(s_img_dir, img_file)
                try:
                    im = cv2.imread(img_path)
                    if im is None or im.size == 0:
                        report["issues"]["corrupted_images"].append(f"{split_name}/{img_file}")
                    else:
                        # Simple hash check for duplicates
                        h = hashlib.md5(im.tobytes()).hexdigest()
                        if h in file_hashes:
                            report["issues"]["duplicate_files"].append(f"{split_name}/{img_file} duplicate of {file_hashes[h]}")
                        else:
                            file_hashes[h] = f"{split_name}/{img_file}"
                except Exception as e:
                    report["issues"]["corrupted_images"].append(f"{split_name}/{img_file} ({str(e)})")

            # Check 4: Label contents & YOLO syntax
            for lbl_file in lbl_files:
                lbl_path = os.path.join(s_lbl_dir, lbl_file)
                try:
                    with open(lbl_path, "r", encoding="utf-8") as lf:
                        lines = [line.strip() for line in lf if line.strip()]
                    
                    if len(lines) == 0:
                        report["issues"]["empty_labels"].append(f"{split_name}/{lbl_file}")
                        continue

                    for line_idx, line in enumerate(lines):
                        parts = line.split()
                        if len(parts) != 5:
                            report["issues"]["invalid_annotations"].append(
                                f"{split_name}/{lbl_file}: line {line_idx+1} has {len(parts)} tokens (expected 5)"
                            )
                            continue

                        cls_str, x_str, y_str, w_str, h_str = parts
                        try:
                            cls_id = int(cls_str)
                            x = float(x_str)
                            y = float(y_str)
                            w = float(w_str)
                            h = float(h_str)

                            # Coordinate range check [0, 1]
                            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 <= w <= 1.0 and 0.0 <= h <= 1.0):
                                report["issues"]["invalid_annotations"].append(
                                    f"{split_name}/{lbl_file}: out-of-range bbox values [{x},{y},{w},{h}]"
                                )
                                continue

                            # Class ID check
                            if declared_classes and cls_id not in declared_classes:
                                report["issues"]["incorrect_class_ids"].append(
                                    f"{split_name}/{lbl_file}: unknown class_id {cls_id}"
                                )

                            # Distribution tally
                            cls_name = declared_classes.get(cls_id, f"Class_{cls_id}")
                            report["class_distribution"][cls_name] = report["class_distribution"].get(cls_name, 0) + 1
                            report["summary"]["valid_annotations"] += 1

                        except ValueError:
                            report["issues"]["invalid_annotations"].append(
                                f"{split_name}/{lbl_file}: non-numeric tokens"
                            )
                except Exception as e:
                    report["issues"]["empty_labels"].append(f"{split_name}/{lbl_file} read error: {e}")

        report["summary"]["classes_detected"] = len(report["class_distribution"])

        # Determine overall validity
        critical_issues = (
            len(report["issues"]["corrupted_images"]) +
            len(report["issues"]["invalid_annotations"]) +
            len(report["issues"]["incorrect_class_ids"])
        )
        report["is_valid"] = critical_issues == 0 and report["summary"]["total_images"] > 0
        return report

    def generate_previews(self, dataset_path: str, max_samples: int = 6) -> List[Dict[str, Any]]:
        """
        Generate sample annotated images with bounding boxes drawn and labeled.
        Returns list of objects with base64 data, file name, and box annotations.
        """
        previews = []
        yaml_path = self._find_yaml(dataset_path)
        declared_classes = {}
        if yaml_path and os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    yd = yaml.safe_load(f)
                    names = yd.get("names", {})
                    if isinstance(names, list):
                        declared_classes = {i: n for i, n in enumerate(names)}
                    elif isinstance(names, dict):
                        declared_classes = {int(k): str(v) for k, v in names.items()}
            except Exception:
                pass

        # Check train images
        candidates = []
        for split in ["train", "val", ""]:
            img_dir = os.path.join(dataset_path, "images", split) if split else dataset_path
            lbl_dir = os.path.join(dataset_path, "labels", split) if split else os.path.join(dataset_path, "labels")

            if os.path.exists(img_dir):
                for f in os.listdir(img_dir):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                        candidates.append((os.path.join(img_dir, f), os.path.join(lbl_dir, os.path.splitext(f)[0] + ".txt"), f))
            if len(candidates) >= max_samples * 2:
                break

        # Select samples
        samples = candidates[:max_samples]

        colors = [
            (99, 102, 241), (6, 182, 212), (16, 185, 129), (245, 158, 11),
            (244, 63, 94), (139, 92, 246), (236, 72, 153)
        ]

        for img_path, lbl_path, fname in samples:
            img = cv2.imread(img_path)
            if img is None:
                continue

            h, w, _ = img.shape
            annotations = []

            if os.path.exists(lbl_path):
                with open(lbl_path, "r") as lf:
                    lines = [l.strip() for l in lf if l.strip()]

                for line in lines:
                    parts = line.split()
                    if len(parts) == 5:
                        try:
                            cls_id = int(parts[0])
                            xc = float(parts[1]) * w
                            yc = float(parts[2]) * h
                            bw = float(parts[3]) * w
                            bh = float(parts[4]) * h

                            x1 = int(xc - bw / 2)
                            y1 = int(yc - bh / 2)
                            x2 = int(xc + bw / 2)
                            y2 = int(yc + bh / 2)

                            cls_name = declared_classes.get(cls_id, f"Class {cls_id}")
                            color = colors[cls_id % len(colors)]

                            # Draw bounding box
                            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

                            # Label pill
                            label_str = f"{cls_name} (#{cls_id})"
                            (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                            cv2.rectangle(img, (x1, max(0, y1 - 20)), (x1 + tw + 8, y1), color, -1)
                            cv2.putText(img, label_str, (x1 + 4, max(14, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

                            annotations.append({
                                "class_id": cls_id,
                                "class_name": cls_name,
                                "box": [x1, y1, x2, y2]
                            })
                        except Exception:
                            pass

            # Resize thumbnail for preview (max width 600)
            if w > 600:
                scale = 600 / w
                img = cv2.resize(img, (600, int(h * scale)))

            _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            b64 = base64.b64encode(buffer).decode("utf-8")

            previews.append({
                "filename": fname,
                "width": w,
                "height": h,
                "annotations_count": len(annotations),
                "annotations": annotations,
                "image_base64": f"data:image/jpeg;base64,{b64}"
            })

        return previews

dataset_manager = DatasetManager()
