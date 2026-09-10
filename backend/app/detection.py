import cv2
import random
from .config import settings

# ── Model loader ──────────────────────────────────────────
_model = None
_simulation_mode = False

def _load_model():
    global _model, _simulation_mode
    try:
        from ultralytics import YOLO
        _model = YOLO(settings.YOLO_MODEL)   # downloads yolov8n.pt on first run
        _simulation_mode = False
        print("[Detection] YOLOv8 model loaded — real detection active.")
    except Exception as e:
        print(f"[Detection] YOLO unavailable ({e}). Running in simulation mode.")
        _simulation_mode = True

_load_model()

# ── Simulation pool ───────────────────────────────────────
# Items that appear in simulation when YOLO isn't running.
# Mix of groceries + stationery + snacks for the shop.
_SIM_ITEMS = [
    # Groceries
    "Apple", "Banana", "Milk (1L)", "Bread", "Eggs (12)",
    "Water Bottle", "Orange", "Carrot", "Coca Cola", "Pepsi", "Sprite",
    # Snacks & Shop items
    "Biscuits", "Lays", "Book", "Pen", "Paper Ream", "Calculator", "Mobile Phone", "Oreo", "KitKat"
]

_SIM_PERSONS = ["Person detected near shelf"]

EXCLUDED_CLASSES = {
    "chair", "table", "dining table", "desk", "office chair", "tie", "necktie", "suit tie"
}


def _label_for_class(cls_id: int, model) -> tuple:
    """
    Returns (category, display_label) for a class id from our YOLO model.
    category is either 'person' or 'item'.
    """
    raw = model.names.get(cls_id, f"object_{cls_id}")
    norm_raw = raw.lower().replace("_", " ").strip()
    if norm_raw in EXCLUDED_CLASSES:
        return None, None
    if norm_raw in ["cell phone", "cellphone", "mobile phone", "mobile"]:
        return "item", "Mobile Phone"
    if norm_raw in ["bottle", "water bottle"]:
        return "item", "Water Bottle"
    if norm_raw in ["milk", "milk (1l)"]:
        return "item", "Milk (1L)"
    if "egg" in norm_raw:
        return "item", "Eggs (12)"
    if "biscuit" in norm_raw:
        return "item", "Biscuits"
    if "lays" in norm_raw:
        return "item", "Lays"
    if "pen" in norm_raw:
        return "item", "Pen"
    if norm_raw == "person":
        return "person", "Person"
    return "item", raw.replace("_", " ").title()


def detect_from_frame(frame):
    """
    Analyse a single OpenCV BGR frame.

    Returns a list of dicts:
      [{"label": str, "confidence": float, "category": "item"|"person"}, ...]

    In simulation mode, randomly generates plausible events (55% chance per frame).
    """
    if _simulation_mode or _model is None:
        if random.random() >= 0.55:
            return []
        # 20 % chance of a person being detected
        if random.random() < 0.20:
            return [{"label": "Person",
                     "confidence": round(random.uniform(0.72, 0.98), 2),
                     "category": "person"}]
        item = random.choice(_SIM_ITEMS)
        return [{"label": item,
                 "confidence": round(random.uniform(0.68, 0.97), 2),
                 "category": "item"}]

    # ── Real YOLO inference ────────────────────────────────
    try:
        results = _model(frame, conf=settings.CONFIDENCE_THRESHOLD, verbose=False)
    except Exception as e:
        print(f"[Detection] YOLO inference error: {e}")
        return []

    detected = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            category, label = _label_for_class(cls_id, _model)
            if category is None or label is None:
                continue
            if label.lower().strip() in EXCLUDED_CLASSES:
                continue
            detected.append({"label": label, "confidence": round(conf, 3), "category": category})
    return detected


def detect_from_stream(stream_url: str):
    """Generator: yields detections per frame from a video stream URL."""
    cap = cv2.VideoCapture(stream_url)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        yield detect_from_frame(frame)
    cap.release()


def simulate_detection(db=None):
    """Simulate a single shelf-removal event for the /detect/simulate endpoint."""
    item = None
    if db is not None:
        try:
            from . import models
            in_stock = db.query(models.Product).filter(models.Product.stock > 0).all()
            if in_stock:
                chosen = random.choice(in_stock)
                item = chosen.name
        except Exception:
            pass

    if not item:
        item = random.choice(_SIM_ITEMS)

    qty = random.randint(1, 2)
    conf = round(random.uniform(0.75, 0.99), 2)
    return {item: {"quantity": qty, "confidence": conf}}