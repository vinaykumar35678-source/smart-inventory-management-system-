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

_CURR_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_CURR_DIR)


def _get_best_model_path():
    # 1. Check active_model.json if configured
    active_json = os.path.join(_ROOT_DIR, "ml", "models", "active_model.json")
    if os.path.exists(active_json):
        try:
            import json
            with open(active_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                m_path = data.get("model_path")
                if m_path and os.path.exists(m_path):
                    return m_path
        except Exception:
            pass

    # 2. Check candidate model paths
    candidates = [
        os.path.join(_ROOT_DIR, "ml", "models", "yolo11_smartshelf_pen_lays_bisc", "best.pt"),
        os.path.join(_ROOT_DIR, "runs", "train", "yolo11_smartshelf_pen_lays_bisc", "weights", "best.pt"),
        os.path.join(_CURR_DIR, "runs", "detect", "smart_shelf_model", "weights", "best.pt"),
        os.path.join(_ROOT_DIR, "runs", "detect", "smart_shelf_model", "weights", "best.pt"),
        os.path.join(_CURR_DIR, "yolo11n.onnx"),
        os.path.join(_ROOT_DIR, "yolo11n.onnx"),
        os.path.join(_CURR_DIR, "yolo11n.pt"),
        os.path.join(_ROOT_DIR, "yolo11n.pt"),
        os.path.join(_CURR_DIR, "yolov8n.pt"),
        os.path.join(_ROOT_DIR, "yolov8n.pt"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "yolo11n.pt"


YOLO_MODEL_PATH = _get_best_model_path()
CONFIDENCE_THRESHOLD  = 0.15


def _load_model():
    global _model, _simulation_mode
    try:
        from ultralytics import YOLO
        _model = YOLO(YOLO_MODEL_PATH)
        _simulation_mode = False
        print(f"[Detection] YOLO loaded ({os.path.basename(YOLO_MODEL_PATH)}) — real detection active.")
    except Exception as exc:
        print(f"[Detection] YOLO unavailable ({exc}). Simulation mode ON.")
        _simulation_mode = True


_load_model()


# ── Class handling ────────────────────────────────────
_SIM_ITEMS = [
    "Apple", "Banana", "Milk", "Bread",
    "Water Bottle", "Lays", "Biscuits", "Cell Phone",
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

            raw_label = _model.names.get(cls_id, f"object_{cls_id}") if hasattr(_model, "names") else f"object_{cls_id}"
            norm_label = raw_label.lower().replace("_", " ").strip()

            if norm_label in ["cell phone", "cellphone", "mobile phone", "mobile"]:
                final_label = "Cell Phone"
            elif "biscuit" in norm_label:
                final_label = "Biscuits"
            elif "lays" in norm_label:
                final_label = "Lays"
            elif "pen" in norm_label:
                final_label = "Pen"
            else:
                final_label = raw_label.replace("_", " ").title()

            # Identify person class robustly regardless of model
            if norm_label == "person":
                detected.append({"label": "Person",
                                  "confidence": round(conf, 3),
                                  "category": "person",
                                  "box": xyxy,
                                  "track_id": track_id})
            else:
                detected.append({"label": final_label,
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
