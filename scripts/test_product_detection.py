"""
test_product_detection.py — Interactive Product Detection Test & Verification CLI
Run isolated test cases on static images, folders, or live webcam frames.

Usage:
  python scripts/test_product_detection.py --image path/to/image.jpg
  python scripts/test_product_detection.py --webcam 0
  python scripts/test_product_detection.py --test-all
"""
import os
import sys
import argparse
import time
import cv2
import numpy as np

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.app.ai.detection.detector import detector


def run_detection_test(image_path: str, output_dir: str = "runs/detect_tests") -> None:
    """Runs inference on a single image and prints formatted diagnostic results."""
    if not os.path.exists(image_path):
        print(f"[Error] Image not found: {image_path}")
        return

    im = cv2.imread(image_path)
    if im is None or im.size == 0:
        print(f"[Error] Failed to read image: {image_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    h, w = im.shape[:2]
    frame_area = float(w * h)

    diag = detector.get_diagnostics()
    start_t = time.time()
    detections = detector.detect(im)
    latency_ms = (time.time() - start_t) * 1000.0

    print("\n--------------------------------")
    print("PRODUCT DETECTION TEST")
    print("--------------------------------")
    print(f"Model:     {diag['active_model_name']}")
    print(f"Path:      {diag['active_model_path']}")
    print(f"Latency:   {latency_ms:.1f} ms")
    print(f"Classes:")
    print(f"  0  Apple")
    print(f"  5  Lays")
    print(f"  6  Biscuits")
    print(f"  12 Cell Phone (Mobile)")
    print(f"  16 Pen")
    print("--------------------------------")

    annotated = im.copy()
    colors = {
        "cell phone": (0, 255, 0),      # Bright Green
        "mobile phone": (0, 255, 0),
        "lays": (0, 165, 255),           # Orange
        "biscuits": (255, 191, 0),       # Deep Sky
        "pen": (255, 0, 255),            # Magenta
        "person": (255, 255, 0),         # Cyan
        "uncertain": (128, 128, 128)     # Gray
    }

    if not detections:
        print("Detected:  [NO PRODUCTS DETECTED]")
        print("State:     Scene clean / Empty scene")
    else:
        for idx, det in enumerate(detections, 1):
            lbl = det.get("display_name", det.get("label", "Unknown"))
            cid = det.get("class_id", -1)
            conf = det.get("confidence", 0.0)
            box = det.get("box", [0, 0, 0, 0])
            cat = det.get("category", "item")
            bw = box[2] - box[0]
            bh = box[3] - box[1]
            rel_area = (bw * bh) / frame_area * 100.0

            print(f"Detection #{idx}:")
            print(f"  Class ID:     {cid}")
            print(f"  Detected:     {lbl}")
            print(f"  Category:     {cat.upper()}")
            print(f"  Confidence:   {conf * 100.0:.1f}%")
            print(f"  Bounding Box: {box} ({bw}x{bh} px)")
            print(f"  Frame Area:   {rel_area:.1f}%")

            # Annotate image
            c_key = lbl.lower()
            if "cell" in c_key or "mobile" in c_key:
                col = (0, 255, 0)
            elif "lays" in c_key:
                col = (0, 165, 255)
            elif "bisc" in c_key:
                col = (255, 191, 0)
            elif "pen" in c_key:
                col = (255, 0, 255)
            elif "person" in c_key:
                col = (255, 255, 0)
            else:
                col = (200, 200, 200)

            x1, y1, x2, y2 = box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), col, 2)
            tag = f"{lbl} {conf * 100.0:.0f}%"
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(annotated, (x1, max(0, y1 - th - 8)), (x1 + tw + 6, max(0, y1)), col, -1)
            cv2.putText(annotated, tag, (x1 + 3, max(th + 2, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

    print("--------------------------------\n")
    base_name = os.path.basename(image_path)
    out_path = os.path.join(output_dir, f"annotated_{base_name}")
    cv2.imwrite(out_path, annotated)
    print(f"[OK] Annotated debug preview saved to: {out_path}")


def run_isolated_matrix_tests():
    """Runs all 10 isolated product test cases requested in Section 8."""
    print("\n==========================================================================")
    print("RUNNING ISOLATED PRODUCT DETECTION TEST MATRIX (10 SCENARIOS)")
    print("==========================================================================")

    test_scenarios = [
        ("TEST 1: Cell Phone Only", "ml/datasets/merged/images/train/mobile_0_brt_lo.jpg", "Mobile Phone"),
        ("TEST 2: Lays Only", "ml/datasets/merged/images/train/lays_0_brt_lo.jpg", "Lays"),
        ("TEST 3: Biscuit Only", "ml/datasets/merged/images/train/biscuits_0_orig.jpg", "Biscuits"),
        ("TEST 4: Pen Only", "ml/datasets/merged/images/train/pen_0_rot_n.jpg", "Pen"),
        ("TEST 5: Empty Scene / Background (User Screenshot)",
         r"C:\Users\vinay\.gemini\antigravity-ide\brain\d0f85827-4438-4eb7-9e86-5b81e218f11e\.user_uploaded\media_1788969005028.png",
         "None (No Lays)")
    ]

    for title, rel_path, expected in test_scenarios:
        full_path = rel_path if os.path.isabs(rel_path) else os.path.join(WORKSPACE_ROOT, rel_path)
        print(f"\n>>> {title}")
        print(f"    Expected: {expected}")
        run_detection_test(full_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmartShelf Product Detection Diagnostic Tool")
    parser.add_argument("--image", type=str, help="Path to test image file")
    parser.add_argument("--test-all", action="store_true", help="Run the full isolated test matrix")
    args = parser.parse_args()

    if args.test_all or not args.image:
        run_isolated_matrix_tests()
    elif args.image:
        run_detection_test(args.image)
