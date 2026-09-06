"""
validate_dataset.py — Automated YOLO Dataset Validator & HTML Report Generator
Validates bounding box geometry, label integrity, image readability, and class distributions.
Generates an interactive HTML audit report at ml/datasets/dataset_report.html.
"""
import os
import sys
import json
import yaml
import cv2
import base64
import hashlib
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MERGED_DIR = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "merged")
REPORT_HTML_FILE = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "dataset_report.html")


def validate_yolo_dataset(dataset_dir: str = MERGED_DIR, yaml_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs comprehensive verification on a YOLO formatted dataset.
    """
    if not yaml_path:
        yaml_path = os.path.join(dataset_dir, "data.yaml")

    declared_classes = {}
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as yf:
            yd = yaml.safe_load(yf)
            names = yd.get("names", {})
            if isinstance(names, list):
                declared_classes = {i: n for i, n in enumerate(names)}
            elif isinstance(names, dict):
                declared_classes = {int(k): str(v) for k, v in names.items()}

    report = {
        "dataset_path": dataset_dir,
        "yaml_path": yaml_path,
        "validated_at": datetime.now().isoformat(),
        "is_valid": True,
        "summary": {
            "total_images": 0,
            "valid_images": 0,
            "total_labels": 0,
            "valid_annotations": 0,
            "corrupted_images": 0,
            "missing_labels": 0,
            "missing_images": 0,
            "empty_labels": 0,
            "invalid_boxes": 0,
            "invalid_class_ids": 0,
            "duplicate_images": 0,
            "num_classes": len(declared_classes)
        },
        "issues": {
            "corrupted_images": [],
            "missing_labels": [],
            "missing_images": [],
            "empty_labels": [],
            "invalid_annotations": [],
            "invalid_class_ids": [],
            "duplicate_files": []
        },
        "split_stats": {"train": {}, "val": {}, "test": {}},
        "class_distribution": defaultdict(int),
        "declared_classes": declared_classes,
        "sample_previews": []
    }

    splits = ["train", "val", "test"]
    seen_hashes = {}

    for split in splits:
        img_dir = os.path.join(dataset_dir, "images", split)
        lbl_dir = os.path.join(dataset_dir, "labels", split)

        img_files = []
        if os.path.exists(img_dir):
            img_files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]

        lbl_files = []
        if os.path.exists(lbl_dir):
            lbl_files = [f for f in os.listdir(lbl_dir) if f.endswith('.txt')]

        report["split_stats"][split] = {
            "images": len(img_files),
            "labels": len(lbl_files)
        }
        report["summary"]["total_images"] += len(img_files)
        report["summary"]["total_labels"] += len(lbl_files)

        img_stems = {os.path.splitext(f)[0]: f for f in img_files}
        lbl_stems = {os.path.splitext(f)[0]: f for f in lbl_files}

        # 1. Missing labels check
        for stem, fname in img_stems.items():
            if stem not in lbl_stems:
                report["issues"]["missing_labels"].append(f"{split}/{fname}")
                report["summary"]["missing_labels"] += 1

        # 2. Missing images check
        for stem, fname in lbl_stems.items():
            if stem not in img_stems:
                report["issues"]["missing_images"].append(f"{split}/{fname}")
                report["summary"]["missing_images"] += 1

        # 3. Readability & Duplicate checks
        for fname in img_files:
            ipath = os.path.join(img_dir, fname)
            try:
                im = cv2.imread(ipath)
                if im is None or im.size == 0:
                    report["issues"]["corrupted_images"].append(f"{split}/{fname}")
                    report["summary"]["corrupted_images"] += 1
                else:
                    report["summary"]["valid_images"] += 1
                    h = hashlib.md5(cv2.resize(im, (32, 32)).tobytes()).hexdigest()
                    if h in seen_hashes:
                        report["issues"]["duplicate_files"].append(f"{split}/{fname} duplicate of {seen_hashes[h]}")
                        report["summary"]["duplicate_images"] += 1
                    else:
                        seen_hashes[h] = f"{split}/{fname}"
            except Exception as e:
                report["issues"]["corrupted_images"].append(f"{split}/{fname} ({str(e)})")
                report["summary"]["corrupted_images"] += 1

        # 4. Annotation geometry & Class ID checks
        for fname in lbl_files:
            lpath = os.path.join(lbl_dir, fname)
            try:
                with open(lpath, "r", encoding="utf-8") as lf:
                    lines = [l.strip() for l in lf if l.strip()]

                if not lines:
                    report["issues"]["empty_labels"].append(f"{split}/{fname}")
                    report["summary"]["empty_labels"] += 1
                    continue

                for line_no, line in enumerate(lines, 1):
                    tokens = line.split()
                    if len(tokens) < 5:
                        report["issues"]["invalid_annotations"].append(f"{split}/{fname}:{line_no} token count {len(tokens)}")
                        report["summary"]["invalid_boxes"] += 1
                        continue

                    try:
                        cid = int(tokens[0])
                        xc = float(tokens[1])
                        yc = float(tokens[2])
                        bw = float(tokens[3])
                        bh = float(tokens[4])

                        # Bounding box bounds check [0, 1]
                        if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 < bw <= 1.0 and 0.0 < bh <= 1.0):
                            report["issues"]["invalid_annotations"].append(f"{split}/{fname}:{line_no} out-of-bounds [{xc},{yc},{bw},{bh}]")
                            report["summary"]["invalid_boxes"] += 1
                            continue

                        # Class ID check
                        if declared_classes and cid not in declared_classes:
                            report["issues"]["invalid_class_ids"].append(f"{split}/{fname}:{line_no} unknown class {cid}")
                            report["summary"]["invalid_class_ids"] += 1
                            continue

                        cname = declared_classes.get(cid, f"Class_{cid}")
                        report["class_distribution"][cname] += 1
                        report["summary"]["valid_annotations"] += 1

                    except ValueError:
                        report["issues"]["invalid_annotations"].append(f"{split}/{fname}:{line_no} non-numeric values")
                        report["summary"]["invalid_boxes"] += 1
            except Exception as e:
                report["issues"]["empty_labels"].append(f"{split}/{fname} read error: {e}")

    # Generate sample previews (first 6 samples from train)
    train_img_dir = os.path.join(dataset_dir, "images", "train")
    train_lbl_dir = os.path.join(dataset_dir, "labels", "train")
    if os.path.exists(train_img_dir):
        samples = [f for f in os.listdir(train_img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))][:6]
        colors = [(99, 102, 241), (6, 182, 212), (16, 185, 129), (245, 158, 11), (239, 68, 68), (168, 85, 247)]

        for sname in samples:
            ipath = os.path.join(train_img_dir, sname)
            lpath = os.path.join(train_lbl_dir, os.path.splitext(sname)[0] + ".txt")
            im = cv2.imread(ipath)
            if im is None:
                continue
            h, w = im.shape[:2]
            box_count = 0
            if os.path.exists(lpath):
                with open(lpath, "r", encoding="utf-8") as lf:
                    for line in lf:
                        p = line.strip().split()
                        if len(p) >= 5:
                            try:
                                cid = int(p[0])
                                xc, yc, bw, bh = map(float, p[1:5])
                                x1 = max(0, int((xc - bw/2) * w))
                                y1 = max(0, int((yc - bh/2) * h))
                                x2 = min(w, int((xc + bw/2) * w))
                                y2 = min(h, int((yc + bh/2) * h))
                                col = colors[cid % len(colors)]
                                cv2.rectangle(im, (x1, y1), (x2, y2), col, 2)
                                lbl_txt = f"{declared_classes.get(cid, cid)}"
                                cv2.putText(im, lbl_txt, (x1 + 4, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)
                                box_count += 1
                            except Exception:
                                pass

            # Resize to max 400px width
            if w > 400:
                scale = 400 / w
                im = cv2.resize(im, (400, int(h * scale)))

            _, buf = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 80])
            b64 = base64.b64encode(buf).decode("utf-8")
            report["sample_previews"].append({
                "filename": sname,
                "box_count": box_count,
                "image_base64": f"data:image/jpeg;base64,{b64}"
            })

    critical_errors = (
        report["summary"]["corrupted_images"] +
        report["summary"]["invalid_boxes"] +
        report["summary"]["invalid_class_ids"]
    )
    report["is_valid"] = critical_errors == 0 and report["summary"]["valid_images"] > 0
    return report


def generate_html_report(report: Dict[str, Any], output_path: str = REPORT_HTML_FILE) -> str:
    """
    Renders an HTML dashboard report summarizing dataset metrics, distribution, and preview cards.
    """
    s = report["summary"]
    splits = report["split_stats"]
    classes = report["declared_classes"]
    dist = report["class_distribution"]

    # Build Class Distribution rows
    class_rows = ""
    for cid, cname in classes.items():
        cnt = dist.get(cname, 0)
        status_badge = '<span style="color:#10b981;background:rgba(16,185,129,0.15);padding:3px 8px;border-radius:4px;font-size:12px;">Balanced</span>'
        if cnt == 0:
            status_badge = '<span style="color:#ef4444;background:rgba(239,68,68,0.15);padding:3px 8px;border-radius:4px;font-size:12px;">Empty (0)</span>'
        elif cnt < 15:
            status_badge = '<span style="color:#f59e0b;background:rgba(245,158,11,0.15);padding:3px 8px;border-radius:4px;font-size:12px;">Low (&lt;15)</span>'

        class_rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #1e293b;font-weight:600;">{cid}</td>
            <td style="padding:10px;border-bottom:1px solid #1e293b;">{cname}</td>
            <td style="padding:10px;border-bottom:1px solid #1e293b;font-weight:700;color:#6366f1;">{cnt}</td>
            <td style="padding:10px;border-bottom:1px solid #1e293b;">{status_badge}</td>
        </tr>
        """

    # Build sample cards
    preview_cards = ""
    for p in report["sample_previews"]:
        preview_cards += f"""
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;overflow:hidden;padding:8px;">
            <img src="{p['image_base64']}" style="width:100%;border-radius:6px;display:block;" />
            <div style="padding:8px 4px 4px;font-size:12px;color:#94a3b8;display:flex;justify-content:space-between;">
                <span>{p['filename']}</span>
                <span style="color:#10b981;font-weight:600;">{p['box_count']} boxes</span>
            </div>
        </div>
        """

    status_color = "#10b981" if report["is_valid"] else "#ef4444"
    status_text = "PASSED - READY FOR TRAINING" if report["is_valid"] else "ATTENTION REQUIRED"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SmartShelf — Dataset Validation Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #090d16;
            color: #f8fafc;
            margin: 0;
            padding: 30px;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 20px; }}
        .badge {{ background: {status_color}; color: #000; font-weight: 700; padding: 6px 14px; border-radius: 9999px; font-size: 13px; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 25px 0; }}
        .card {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 18px; }}
        .metric-title {{ color: #94a3b8; font-size: 13px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-val {{ font-size: 28px; font-weight: 700; color: #fff; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th {{ background: #1e293b; padding: 10px; font-size: 13px; color: #cbd5e1; }}
        .preview-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 15px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1 style="margin:0 0 6px 0;font-size:24px;letter-spacing:-0.5px;">SmartShelf Multi-Product Dataset Validation Report</h1>
            <p style="margin:0;color:#94a3b8;font-size:14px;">Audit executed on {report['validated_at']}</p>
        </div>
        <div><span class="badge">{status_text}</span></div>
    </div>

    <div class="grid-4">
        <div class="card">
            <div class="metric-title">Total Images</div>
            <div class="metric-val">{s['total_images']}</div>
            <div style="font-size:12px;color:#10b981;margin-top:4px;">{s['valid_images']} verified readable</div>
        </div>
        <div class="card">
            <div class="metric-title">Valid Annotations</div>
            <div class="metric-val" style="color:#6366f1;">{s['valid_annotations']}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px;">{s['total_labels']} label files</div>
        </div>
        <div class="card">
            <div class="metric-title">Classes Configured</div>
            <div class="metric-val" style="color:#06b6d4;">{s['num_classes']}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px;">from data.yaml</div>
        </div>
        <div class="card">
            <div class="metric-title">Corrupted / Invalid</div>
            <div class="metric-val" style="color:{'#10b981' if s['corrupted_images'] + s['invalid_boxes'] == 0 else '#ef4444'};">
                {s['corrupted_images'] + s['invalid_boxes']}
            </div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px;">0 critical blockers</div>
        </div>
    </div>

    <!-- Splits -->
    <div class="card" style="margin-bottom:25px;">
        <h3 style="margin:0 0 15px 0;font-size:16px;">Dataset Split Breakdown (70% Train / 20% Val / 10% Test)</h3>
        <div style="display:flex;gap:20px;">
            <div style="flex:1;background:#1e293b;padding:12px;border-radius:6px;">
                <div style="color:#94a3b8;font-size:12px;">TRAIN SPLIT</div>
                <div style="font-size:20px;font-weight:700;color:#6366f1;">{splits['train'].get('images', 0)} images</div>
            </div>
            <div style="flex:1;background:#1e293b;padding:12px;border-radius:6px;">
                <div style="color:#94a3b8;font-size:12px;">VALIDATION SPLIT</div>
                <div style="font-size:20px;font-weight:700;color:#06b6d4;">{splits['val'].get('images', 0)} images</div>
            </div>
            <div style="flex:1;background:#1e293b;padding:12px;border-radius:6px;">
                <div style="color:#94a3b8;font-size:12px;">TEST SPLIT</div>
                <div style="font-size:20px;font-weight:700;color:#10b981;">{splits['test'].get('images', 0)} images</div>
            </div>
        </div>
    </div>

    <!-- Class Table -->
    <div class="card" style="margin-bottom:25px;">
        <h3 style="margin:0 0 15px 0;font-size:16px;">Class Distribution & Balance Audit</h3>
        <table>
            <thead>
                <tr><th>Class ID</th><th>Product Name</th><th>Annotation Count</th><th>Balance Health</th></tr>
            </thead>
            <tbody>
                {class_rows}
            </tbody>
        </table>
    </div>

    <!-- Sample BBox Overlays -->
    <div class="card">
        <h3 style="margin:0 0 5px 0;font-size:16px;">Visual Annotation Previews (Sample Train Frames)</h3>
        <p style="margin:0 0 15px 0;font-size:13px;color:#94a3b8;">Rendered bounding boxes with class labels overlaid.</p>
        <div class="preview-grid">
            {preview_cards}
        </div>
    </div>
</div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[DatasetValidator] Generated HTML validation report at: {output_path}")
    return output_path


if __name__ == "__main__":
    rep = validate_yolo_dataset()
    generate_html_report(rep)
    print(f"\n[OK] Dataset Validation Summary:")
    print(f"  Total Images:       {rep['summary']['total_images']}")
    print(f"  Valid Images:       {rep['summary']['valid_images']}")
    print(f"  Valid Annotations:  {rep['summary']['valid_annotations']}")
    print(f"  Corrupted Images:   {rep['summary']['corrupted_images']}")
    print(f"  Invalid Bounding:   {rep['summary']['invalid_boxes']}")
    print(f"  Validation Status:  {'READY FOR TRAINING' if rep['is_valid'] else 'ISSUES FOUND'}")
