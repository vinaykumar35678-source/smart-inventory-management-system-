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
# Mix of groceries + stationery + electronics for the shop.
_SIM_ITEMS = [
    # Groceries
    "Apple", "Banana", "Milk (1L)", "Bread", "Eggs (12)",
    "Bottle (Water)", "Orange", "Carrot", "Sandwich", "Cake",
    # New shop items
    "Mobile Phone", "Book", "Pen", "Paper Ream", "Calculator",
]

_SIM_PERSONS = ["Person detected near shelf"]


def _label_for_class(cls_id: int, model) -> tuple:
    """
    Returns (category, display_label) for a class id from our custom YOLOv11 model.
    category is either 'person' or 'item'.
    """
    raw = model.names.get(cls_id, f"object_{cls_id}")
    if raw.lower() == "person":
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


def simulate_detection():
    """Simulate a single shelf-removal event for the /detect/simulate endpoint."""
    if random.random() < 0.25:
        return {}
    item  = random.choice(_SIM_ITEMS)
    qty   = random.randint(1, 3)
    conf  = round(random.uniform(0.65, 0.99), 2)
    return {item: {"quantity": qty, "confidence": conf}}