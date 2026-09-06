"""
detection.py  — YOLO11 wrapper with simulation fallback
Objective 1: Automate Product Detection using YOLO11
Objective 3: Detect Product Removal via differential frame comparison
"""
import cv2
import random
import os
from collections import Counter

# ── Model loader ───────────────────────────────────────────────────────────
_model           = None
_simulation_mode = False

# Use custom trained model if available, otherwise fallback to ONNX or PT
if os.path.exists("runs/detect/smart_shelf_model/weights/best.pt"):
    YOLO_MODEL_PATH = "runs/detect/smart_shelf_model/weights/best.pt"
elif os.path.exists("yolo11n.onnx"):
    YOLO_MODEL_PATH = "yolo11n.onnx"
else:
    YOLO_MODEL_PATH = "yolo11n.pt"

CONFIDENCE_THRESHOLD  = 0.15


def _load_model():
    global _model, _simulation_mode
    try:
        from ultralytics import YOLO
        _model           = YOLO(YOLO_MODEL_PATH)
        _simulation_mode = False
        print("[Detection] YOLO11 loaded — real detection active.")
    except Exception as exc:
        print(f"[Detection] YOLO unavailable ({exc}). Simulation mode ON.")
        _simulation_mode = True


_load_model()


# ── Class handling ────────────────────────────────────
_SIM_ITEMS = [
    "Apple", "Banana", "Milk", "Bread",
    "Water Bottle", "Lays", "Biscuits", "Mobile",
    "Chair", "Table", "Book", "Pen", "ID Card"
]


# ── Differential detection ──────────────────────────────────
_previous_counts: dict = {}
_detection_phase: dict = {}  # Tracks detection phase per product (0 = pending addition, 1 = pending removal)


def reset_frame_tracking():
    global _previous_counts
    _previous_counts = {}


def compare_frames(current_items: list) -> tuple:
    """
    Compare current detected items with the previous frame:
    - If count increases: mark ADDITION.
    - If count decreases: mark REMOVAL.
    """
    global _previous_counts
    current_counts = Counter(current_items)
    added = {}
    removed = {}

    all_keys = set(_previous_counts.keys()).union(set(current_counts.keys()))

    for item in all_keys:
        prev_qty = _previous_counts.get(item, 0)
        curr_qty = current_counts.get(item, 0)
        
        if curr_qty > prev_qty:
            added[item] = curr_qty - prev_qty
        elif curr_qty < prev_qty:
            removed[item] = prev_qty - curr_qty

    _previous_counts = dict(current_counts)
    return added, removed


# ── Core detection function ───────────────────────────────────────────────
def detect_from_frame(frame) -> list:
    """
    Analyse a single OpenCV BGR frame.
    Returns list of dicts: [{label, confidence, category, box: [x1, y1, x2, y2]}, ...]
    Falls back to simulation when YOLO is not available.
    """
    if _simulation_mode or _model is None:
        if random.random() >= 0.55:
            return []
        if random.random() < 0.20:
            return [{"label": "Person",
                     "confidence": round(random.uniform(0.72, 0.98), 2),
                     "category": "person",
                     "box": [120, 100, 320, 420]}]
        item = random.choice(_SIM_ITEMS)
        return [{"label": item,
                 "confidence": round(random.uniform(0.68, 0.97), 2),
                 "category": "item",
                 "box": [180, 140, 380, 340]}]

    # Real YOLO11 inference with ByteTrack enabled for stability
    try:
        results = _model.track(frame, imgsz=640, conf=CONFIDENCE_THRESHOLD, persist=True, tracker="bytetrack.yaml", verbose=False)
    except Exception as exc:
        print(f"[Detection] Inference error: {exc}")
        return []

    detected = []
    for r in results:
        if r.boxes is None or len(r.boxes) == 0:
            continue
            
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            xyxy   = [int(x) for x in box.xyxy[0].tolist()]
            track_id = int(box.id[0]) if box.id is not None else None

            raw_label = _model.names.get(cls_id, f"object_{cls_id}")
            # Identify person class robustly regardless of model
            if raw_label.lower() == "person":
                detected.append({"label": "Person",
                                  "confidence": round(conf, 3),
                                  "category": "person",
                                  "box": xyxy,
                                  "track_id": track_id})
            else:
                # Custom models might use underscores, title format looks better
                detected.append({"label": raw_label.replace("_", " ").title(),
                                  "confidence": round(conf, 3),
                                  "category": "item",
                                  "box": xyxy,
                                  "track_id": track_id})
    return detected


def simulate_one_event() -> dict:
    """Return a simulated single removal event dict: {product: {qty, conf}}"""
    if random.random() < 0.25:
        return {}
    item = random.choice(_SIM_ITEMS)
    qty  = random.randint(1, 3)
    conf = round(random.uniform(0.65, 0.99), 2)
    return {item: {"quantity": qty, "confidence": conf}}
