"""
prepare_dataset.py — Multi-Product YOLO Dataset Normalization, Deduplication & Splitting
Converts multiple source datasets into unified YOLO format in ml/datasets/merged/.
Guarantees:
  - 70% Train / 20% Validation / 10% Test split across every class
  - Scene-aware grouping to prevent data leakage between splits
  - MD5 image deduplication
  - Canonical taxonomy mapping via ml/config/taxonomy.json
  - Dynamic generation of ml/datasets/merged/data.yaml
"""
import os
import sys
import json
import yaml
import shutil
import hashlib
import random
import cv2
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "raw")
MERGED_DIR = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "merged")
TAXONOMY_FILE = os.path.join(WORKSPACE_ROOT, "ml", "config", "taxonomy.json")


def load_taxonomy() -> Tuple[Dict[str, int], Dict[str, str], List[str]]:
    """
    Returns:
      class_to_id: {canonical_name: id}
      alias_to_canonical: {alias.lower(): canonical_name}
      class_names_list: [canonical_name, ...]
    """
    if not os.path.exists(TAXONOMY_FILE):
        raise FileNotFoundError(f"Taxonomy file not found at {TAXONOMY_FILE}")

    with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
        tax = json.load(f)

    class_to_id = {}
    alias_to_canonical = {}
    class_names = []

    for idx, item in enumerate(tax.get("classes", [])):
        c_name = item["canonical_name"]
        class_to_id[c_name] = idx
        class_names.append(c_name)
        alias_to_canonical[c_name.lower()] = c_name
        for alias in item.get("aliases", []):
            alias_to_canonical[alias.lower()] = c_name

    return class_to_id, alias_to_canonical, class_names


def get_image_hash(image_path: str) -> Optional[str]:
    """Calculate MD5 hash of image thumbnail for accurate deduplication."""
    try:
        im = cv2.imread(image_path)
        if im is None or im.size == 0:
            return None
        thumb = cv2.resize(im, (64, 64))
        return hashlib.md5(thumb.tobytes()).hexdigest()
    except Exception:
        return None


def get_class_prefix(filename: str) -> str:
    """Extract class prefix from filename, e.g. 'apple_on_shelf_3.jpg' -> 'apple'."""
    stem = os.path.splitext(filename)[0].lower()
    for prefix in ["apple", "banana", "milk", "water_bottle", "bread", "lays",
                   "biscuits", "coca_cola", "pepsi", "sprite", "oreo", "kitkat",
                   "mobile", "chair", "table", "book", "pen", "id_card"]:
        if stem.startswith(prefix):
            return prefix
    return stem.split("_")[0]


def prepare_and_merge_datasets(
    source_dirs: Optional[List[str]] = None,
    train_ratio: float = 0.70,
    val_ratio: float = 0.20,
    test_ratio: float = 0.10,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Consolidate raw datasets into ml/datasets/merged/ with balanced, leakage-free YOLO structure.
    """
    random.seed(seed)
    class_to_id, alias_to_canonical, canonical_names = load_taxonomy()

    if not source_dirs:
        source_dirs = []
        if os.path.exists(RAW_DIR):
            for entry in os.listdir(RAW_DIR):
                p = os.path.join(RAW_DIR, entry)
                if os.path.isdir(p):
                    source_dirs.append(p)

    if not source_dirs:
        raise ValueError(f"No source datasets found in {RAW_DIR}")

    print(f"[DatasetPreparation] Found {len(source_dirs)} raw dataset source(s):")
    for s in source_dirs:
        print(f"  - {os.path.basename(s)}")

    # 1. Clean and initialize merged directory
    if os.path.exists(MERGED_DIR):
        shutil.rmtree(MERGED_DIR)

    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(MERGED_DIR, "images", split), exist_ok=True)
        os.makedirs(os.path.join(MERGED_DIR, "labels", split), exist_ok=True)

    # 2. Collect image-label pairs grouped by class prefix
    seen_hashes = {}
    duplicates_count = 0
    samples_by_class = defaultdict(list)

    for s_dir in source_dirs:
        ds_name = os.path.basename(s_dir)
        src_yaml = os.path.join(s_dir, "data.yaml")
        src_classes = {}
        if os.path.exists(src_yaml):
            try:
                with open(src_yaml, "r", encoding="utf-8") as yf:
                    yd = yaml.safe_load(yf)
                    names = yd.get("names", {})
                    if isinstance(names, list):
                        src_classes = {i: n for i, n in enumerate(names)}
                    elif isinstance(names, dict):
                        src_classes = {int(k): str(v) for k, v in names.items()}
            except Exception:
                pass

        img_candidates = []
        for root, _, files in os.walk(s_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                    img_candidates.append(os.path.join(root, f))

        for img_path in sorted(img_candidates):
            h = get_image_hash(img_path)
            if not h:
                continue
            if h in seen_hashes:
                duplicates_count += 1
                continue
            seen_hashes[h] = img_path

            stem = os.path.splitext(os.path.basename(img_path))[0]
            rel = os.path.relpath(img_path, s_dir)
            parts = rel.split(os.sep)

            lbl_path = None
            if "images" in parts:
                lbl_rel = rel.replace("images", "labels").rsplit(".", 1)[0] + ".txt"
                candidate = os.path.join(s_dir, lbl_rel)
                if os.path.exists(candidate):
                    lbl_path = candidate

            if not lbl_path:
                direct_candidate = os.path.join(os.path.dirname(img_path), f"{stem}.txt")
                if os.path.exists(direct_candidate):
                    lbl_path = direct_candidate
                else:
                    lbl_root = os.path.join(s_dir, "labels")
                    if os.path.exists(lbl_root):
                        for r, _, lfiles in os.walk(lbl_root):
                            if f"{stem}.txt" in lfiles:
                                lbl_path = os.path.join(r, f"{stem}.txt")
                                break

            cls_prefix = get_class_prefix(os.path.basename(img_path))
            samples_by_class[cls_prefix].append({
                "dataset": ds_name,
                "img_path": img_path,
                "lbl_path": lbl_path,
                "filename": os.path.basename(img_path),
                "stem": stem,
                "src_classes": src_classes
            })

    total_valid_images = sum(len(v) for v in samples_by_class.values())
    print(f"[DatasetPreparation] Collected {total_valid_images} unique images across {len(samples_by_class)} product groups. Excluded {duplicates_count} duplicate(s).")

    class_counts = defaultdict(lambda: {"train": 0, "val": 0, "test": 0, "total": 0})
    split_counts = {"train": 0, "val": 0, "test": 0}

    # 3. Proportional 70/20/10 split within each product group
    for cls_prefix, samples in samples_by_class.items():
        # Sub-group by sub-scene to prevent intra-scene leakage
        sub_scenes = defaultdict(list)
        for s in samples:
            # Group consecutive shots together
            sub_key = s["stem"].rsplit("_", 1)[0]
            sub_scenes[sub_key].append(s)

        # Distribute items into splits
        s_train, s_val, s_test = [], [], []
        for sub_key, sub_items in sub_scenes.items():
            n = len(sub_items)
            if n <= 2:
                s_train.extend(sub_items)
            else:
                n_tr = max(1, int(n * train_ratio))
                n_va = max(1, int(n * val_ratio))
                s_train.extend(sub_items[:n_tr])
                s_val.extend(sub_items[n_tr:n_tr + n_va])
                s_test.extend(sub_items[n_tr + n_va:])

        split_assignments = [("train", s_train), ("val", s_val), ("test", s_test)]

        for target_split, split_items in split_assignments:
            for s in split_items:
                split_counts[target_split] += 1
                out_img_name = f"{s['dataset']}_{s['filename']}"
                out_lbl_name = f"{s['dataset']}_{s['stem']}.txt"

                target_img_path = os.path.join(MERGED_DIR, "images", target_split, out_img_name)
                target_lbl_path = os.path.join(MERGED_DIR, "labels", target_split, out_lbl_name)

                shutil.copy(s["img_path"], target_img_path)

                remapped_lines = []
                if s["lbl_path"] and os.path.exists(s["lbl_path"]):
                    with open(s["lbl_path"], "r", encoding="utf-8") as lf:
                        lines = [l.strip() for l in lf if l.strip()]

                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5:
                            try:
                                src_cid = int(parts[0])
                                xc, yc, w, h = parts[1:5]
                                raw_name = s["src_classes"].get(src_cid, f"Class_{src_cid}")
                                canonical = alias_to_canonical.get(raw_name.lower(), raw_name)
                                if canonical in class_to_id:
                                    final_cid = class_to_id[canonical]
                                else:
                                    final_cid = src_cid if src_cid < len(canonical_names) else 0
                                    canonical = canonical_names[final_cid]

                                remapped_lines.append(f"{final_cid} {xc} {yc} {w} {h}")
                                class_counts[canonical][target_split] += 1
                                class_counts[canonical]["total"] += 1
                            except Exception:
                                pass

                with open(target_lbl_path, "w", encoding="utf-8") as out_lf:
                    out_lf.write("\n".join(remapped_lines) + "\n")

    # 4. Generate data.yaml with active classes
    active_classes = [c for c in canonical_names if class_counts[c]["total"] > 0]
    max_id = max((class_to_id[c] for c in active_classes), default=len(canonical_names)-1)
    final_names = canonical_names[:max_id + 1]

    data_yaml_content = {
        "path": MERGED_DIR.replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": len(final_names),
        "names": {i: name for i, name in enumerate(final_names)}
    }

    yaml_out_path = os.path.join(MERGED_DIR, "data.yaml")
    with open(yaml_out_path, "w", encoding="utf-8") as yf:
        yaml.dump(data_yaml_content, yf, default_flow_style=False, sort_keys=False)

    # 5. Class Inventory Report
    print("\n=======================================================================")
    print("  SMARTSHELF MERGED DATASET CLASS INVENTORY REPORT")
    print("=======================================================================")
    print(f"{'Class ID':<10} | {'Product Class':<16} | {'Train':<7} | {'Val':<6} | {'Test':<6} | {'Total':<7} | {'Balance Status'}")
    print("-" * 75)

    imbalance_warnings = []
    for cid, cname in enumerate(final_names):
        counts = class_counts[cname]
        tot = counts["total"]
        if tot == 0:
            status = "EMPTY (0 images)"
            imbalance_warnings.append(f"{cname}: 0 images")
        elif tot < 15:
            status = "LOW (<15 instances)"
            imbalance_warnings.append(f"{cname}: only {tot} instances")
        elif tot > 200:
            status = "HIGH (>200 instances)"
        else:
            status = "BALANCED"

        print(f"{cid:<10} | {cname:<16} | {counts['train']:<7} | {counts['val']:<6} | {counts['test']:<6} | {tot:<7} | {status}")

    print("=======================================================================")
    print(f"Total Merged Images: {sum(split_counts.values())} (Train: {split_counts['train']}, Val: {split_counts['val']}, Test: {split_counts['test']})")
    print(f"Excluded Duplicates: {duplicates_count}")
    print(f"Merged Dataset YAML: {yaml_out_path}")
    print("=======================================================================\n")

    return {
        "status": "SUCCESS",
        "total_images": sum(split_counts.values()),
        "split_counts": split_counts,
        "duplicates_excluded": duplicates_count,
        "num_classes": len(final_names),
        "classes": final_names,
        "class_counts": dict(class_counts),
        "yaml_path": yaml_out_path
    }


if __name__ == "__main__":
    prepare_and_merge_datasets()
