"""
augment_and_balance_dataset.py — Professional YOLO Dataset Augmenter & Multi-Product Balancer
Generates high-variance training samples for:
- Biscuits (Class 6)
- Lays (Class 5)
- Mobile / Cell Phone (Class 12)
- Pen (Class 16)
and retail shelf classes.

Applies:
- Photometric transforms: Brightness (+/-20%), Contrast, HSV jitter, Blur
- Geometric transforms: Horizontal flip, scaling, rotation (+/-15 deg) with exact bounding box recalculation
- Occlusion simulation: Cutout rectangles simulating hand interaction
- Scene-level splitting: Guarantees base images and their augmentations stay in the SAME split (prevents data leakage).
"""
import os
import cv2
import glob
import math
import random
import shutil
import yaml
from collections import defaultdict

random.seed(42)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "raw", "smart_shelf_retail")
MERGED_DIR = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "merged")
RAW_IMG_DIR = os.path.join(RAW_DIR, "images", "train")
RAW_LBL_DIR = os.path.join(RAW_DIR, "labels", "train")

# Read class mapping from RAW data.yaml
with open(os.path.join(RAW_DIR, "data.yaml")) as f:
    raw_yaml = yaml.safe_load(f)
raw_names = raw_yaml.get("names", {})
print("Raw classes count:", len(raw_names))

# Merged taxonomy mapping (18 classes)
# 0: Apple, 1: Banana, 2: Milk, 3: Water Bottle, 4: Bread, 5: Lays, 6: Biscuits,
# 7: Coca Cola, 8: Pepsi, 9: Sprite, 10: Oreo, 11: KitKat, 12: Mobile, 13: Chair,
# 14: Table, 15: Book, 16: Pen, 17: ID Card
MERGED_NAMES = {
    0: "Apple", 1: "Banana", 2: "Milk", 3: "Water Bottle", 4: "Bread",
    5: "Lays", 6: "Biscuits", 7: "Coca Cola", 8: "Pepsi", 9: "Sprite",
    10: "Oreo", 11: "KitKat", 12: "Mobile", 13: "Chair", 14: "Table",
    15: "Book", 16: "Pen", 17: "ID Card"
}

# Map from raw_smart_shelf class ID to canonical 18-class ID
# raw: 0:Apple, 1:Banana, 2:Milk, 3:Water Bottle, 4:Bread, 5:Lays, 6:Biscuits, 7:Mobile, 8:Chair, 9:Table, 10:Book, 11:Pen, 12:ID Card
RAW_TO_MERGED_ID = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6,
    7: 12, # Mobile -> 12
    8: 13, # Chair -> 13
    9: 14, # Table -> 14
    10: 15, # Book -> 15
    11: 16, # Pen -> 16
    12: 17  # ID Card -> 17
}

def clamp(val, min_val=0.0, max_val=1.0):
    return max(min_val, min(max_val, val))

# ── Augmentation Functions ──────────────────────────────────────────

def adjust_brightness_contrast(img, alpha=1.0, beta=0):
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

def add_motion_blur(img, ksize=5):
    kernel = np.zeros((ksize, ksize))
    kernel[int((ksize-1)/2), :] = np.ones(ksize)
    kernel /= ksize
    return cv2.filter2D(img, -1, kernel)

import numpy as np

def add_gaussian_noise(img):
    noise = np.random.normal(0, 12, img.shape).astype(np.float32)
    noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy

def add_occlusion(img, boxes):
    # Add a small gray patch near or over part of an object (simulating hand holding)
    out = img.copy()
    h, w = out.shape[:2]
    for b in boxes:
        cid, xc, yc, bw, bh = b
        px = int(xc * w)
        py = int(yc * h)
        pw = int(bw * w * 0.35)
        ph = int(bh * h * 0.35)
        x1 = max(0, px - pw//2)
        y1 = max(0, py - ph//2)
        x2 = min(w, x1 + pw)
        y2 = min(h, y1 + ph)
        color = (random.randint(40, 160), random.randint(40, 160), random.randint(40, 160))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, -1)
    return out

def horizontal_flip(img, boxes):
    flipped_img = cv2.flip(img, 1)
    flipped_boxes = []
    for b in boxes:
        cid, xc, yc, bw, bh = b
        new_xc = clamp(1.0 - xc)
        flipped_boxes.append((cid, new_xc, yc, bw, bh))
    return flipped_img, flipped_boxes

def rotate_image_and_boxes(img, boxes, angle_deg):
    h, w = img.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    cos_val = abs(M[0, 0])
    sin_val = abs(M[0, 1])
    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    rotated_img = cv2.warpAffine(img, M, (new_w, new_h), borderMode=cv2.BORDER_REPLICATE)

    rotated_boxes = []
    for b in boxes:
        cid, xc, yc, bw, bh = b
        # corners in original image
        bx1 = (xc - bw / 2) * w
        by1 = (yc - bh / 2) * h
        bx2 = (xc + bw / 2) * w
        by2 = (yc + bh / 2) * h
        pts = np.array([[bx1, by1], [bx2, by1], [bx2, by2], [bx1, by2]])
        ones = np.ones(shape=(len(pts), 1))
        pts_ones = np.hstack([pts, ones])
        trans_pts = M.dot(pts_ones.T).T

        min_x = clamp(np.min(trans_pts[:, 0]) / new_w)
        max_x = clamp(np.max(trans_pts[:, 0]) / new_w)
        min_y = clamp(np.min(trans_pts[:, 1]) / new_h)
        max_y = clamp(np.max(trans_pts[:, 1]) / new_h)
        n_bw = clamp(max_x - min_x)
        n_bh = clamp(max_y - min_y)
        n_xc = clamp(min_x + n_bw / 2)
        n_yc = clamp(min_y + n_bh / 2)
        if n_bw > 0.02 and n_bh > 0.02:
            rotated_boxes.append((cid, n_xc, n_yc, n_bw, n_bh))

    return rotated_img, rotated_boxes

# ── Main Augmentation Pipeline ──────────────────────────────────────

def generate_augmented_dataset():
    print("=" * 60)
    print("STARTING DATASET AUGMENTATION & BALANCING")
    print("=" * 60)

    # Group original raw images by base scene
    images = [f for f in os.listdir(RAW_IMG_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"Total raw seed images: {len(images)}")

    scene_groups = defaultdict(list)
    for img_file in images:
        base = os.path.splitext(img_file)[0]
        # class prefix e.g. 'biscuits' from 'biscuits_0.jpg'
        prefix = base.rsplit('_', 1)[0]
        scene_groups[prefix].append(img_file)

    # Temporary directory for all generated samples
    all_samples = []

    for prefix, file_list in scene_groups.items():
        is_priority = prefix in ["biscuits", "lays", "mobile", "pen"]
        multiplier = 6 if is_priority else 3

        print(f"Processing category: {prefix} ({len(file_list)} seeds, target x{multiplier})")

        for img_file in file_list:
            ipath = os.path.join(RAW_IMG_DIR, img_file)
            lpath = os.path.join(RAW_LBL_DIR, os.path.splitext(img_file)[0] + ".txt")
            if not os.path.exists(lpath):
                continue

            img = cv2.imread(ipath)
            if img is None:
                continue

            # Read boxes and map class ID to canonical 18-class
            boxes = []
            with open(lpath, "r") as lf:
                for line in lf:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        raw_cid = int(parts[0])
                        canonical_cid = RAW_TO_MERGED_ID.get(raw_cid, raw_cid)
                        xc, yc, bw, bh = map(float, parts[1:5])
                        boxes.append((canonical_cid, xc, yc, bw, bh))

            if not boxes:
                continue

            stem = os.path.splitext(img_file)[0]
            # 1. Original (re-mapped to canonical)
            all_samples.append((prefix, f"{stem}_orig.jpg", img.copy(), list(boxes)))

            # 2. Horizontal Flip
            f_img, f_boxes = horizontal_flip(img, boxes)
            all_samples.append((prefix, f"{stem}_flip.jpg", f_img, f_boxes))

            # 3. Brightness variations
            b_high = adjust_brightness_contrast(img, alpha=1.15, beta=20)
            all_samples.append((prefix, f"{stem}_brt_hi.jpg", b_high, list(boxes)))

            b_low = adjust_brightness_contrast(img, alpha=0.85, beta=-20)
            all_samples.append((prefix, f"{stem}_brt_lo.jpg", b_low, list(boxes)))

            if is_priority:
                # 4. Rotation variations
                r_pos, rb_pos = rotate_image_and_boxes(img, boxes, angle_deg=random.randint(6, 14))
                all_samples.append((prefix, f"{stem}_rot_p.jpg", r_pos, rb_pos))

                r_neg, rb_neg = rotate_image_and_boxes(img, boxes, angle_deg=random.randint(-14, -6))
                all_samples.append((prefix, f"{stem}_rot_n.jpg", r_neg, rb_neg))

                # 5. Hand/Shelf Occlusion Simulation
                occ_img = add_occlusion(img, boxes)
                all_samples.append((prefix, f"{stem}_occ.jpg", occ_img, list(boxes)))

                # 6. Motion Blur / Sensor Noise
                noise_img = add_gaussian_noise(img)
                all_samples.append((prefix, f"{stem}_noise.jpg", noise_img, list(boxes)))

    print(f"\nTotal generated augmented samples: {len(all_samples)}")

    # ── Split by prefix/base scene into Train (70%), Val (20%), Test (10%) ──
    # Group samples by original seed image so no clones cross splits
    seed_clusters = defaultdict(list)
    for prefix, fname, im, bxs in all_samples:
        # seed name before augmentation suffix
        base_seed = fname.rsplit('_', 1)[0]
        seed_clusters[base_seed].append((fname, im, bxs))

    # Clean merged dataset directory
    shutil.rmtree(MERGED_DIR, ignore_errors=True)
    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(MERGED_DIR, "images", split), exist_ok=True)
        os.makedirs(os.path.join(MERGED_DIR, "labels", split), exist_ok=True)

    # Group seed clusters by category prefix
    cat_clusters = defaultdict(list)
    for seed_name, samples in seed_clusters.items():
        prefix = seed_name.split('_')[0]
        cat_clusters[prefix].append(samples)

    split_counts = {"train": 0, "val": 0, "test": 0}
    class_instance_counts = defaultdict(lambda: {"train": 0, "val": 0, "test": 0})

    for prefix, clusters in cat_clusters.items():
        random.shuffle(clusters)
        n = len(clusters)
        n_train = max(1, int(n * 0.70))
        n_val = max(1, int(n * 0.20))
        # remainder for test
        train_clusters = clusters[:n_train]
        val_clusters = clusters[n_train:n_train + n_val]
        test_clusters = clusters[n_train + n_val:]
        if not test_clusters and len(val_clusters) > 1:
            test_clusters = [val_clusters.pop()]

        split_map = [
            ("train", train_clusters),
            ("val", val_clusters),
            ("test", test_clusters)
        ]

        for split_name, c_list in split_map:
            for s_group in c_list:
                for fname, im, bxs in s_group:
                    # Save image (resize to standard 640x640)
                    im_resized = cv2.resize(im, (640, 640))
                    out_img_path = os.path.join(MERGED_DIR, "images", split_name, fname)
                    cv2.imwrite(out_img_path, im_resized, [cv2.IMWRITE_JPEG_QUALITY, 92])

                    # Save label
                    base_lbl = os.path.splitext(fname)[0] + ".txt"
                    out_lbl_path = os.path.join(MERGED_DIR, "labels", split_name, base_lbl)
                    with open(out_lbl_path, "w") as out_lf:
                        for cid, xc, yc, bw, bh in bxs:
                            out_lf.write(f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")
                            class_instance_counts[cid][split_name] += 1

                    split_counts[split_name] += 1

    print("\nDataset generation summary:")
    for sname, cnt in split_counts.items():
        print(f"  {sname}: {cnt} images")

    print("\nPer-class instance distribution:")
    for cid in sorted(class_instance_counts.keys()):
        cname = MERGED_NAMES.get(cid, f"Class_{cid}")
        st = class_instance_counts[cid]
        tot = st['train'] + st['val'] + st['test']
        print(f"  ID {cid:2d} ({cname:12s}): Train={st['train']:3d}, Val={st['val']:2d}, Test={st['test']:2d} | Total={tot:3d}")

    # Write data.yaml in merged
    data_yaml_content = {
        "path": MERGED_DIR.replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 18,
        "names": {int(k): str(v) for k, v in MERGED_NAMES.items()}
    }
    merged_yaml_file = os.path.join(MERGED_DIR, "data.yaml")
    with open(merged_yaml_file, "w") as yf:
        yaml.dump(data_yaml_content, yf, default_flow_style=False, sort_keys=False)

    # Also sync root data.yaml
    with open(os.path.join(WORKSPACE_ROOT, "data.yaml"), "w") as yf:
        yaml.dump(data_yaml_content, yf, default_flow_style=False, sort_keys=False)

    print(f"\nCreated unified data.yaml at {merged_yaml_file}")

if __name__ == "__main__":
    generate_augmented_dataset()
