import os
import cv2
import json
import torch
import numpy as np
from typing import List, Dict, Any, Optional
from ..config.config import ai_config

# Path to authoritative single-source-of-truth class mapping
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))
CLASS_MAPPING_FILE = os.path.join(CONFIG_DIR, "class_mapping.json")


class YOLODetector:
    """
    Production Object Detector powered by Ultralytics YOLO.
    Features:
      - Authoritative single-source-of-truth class mapping (YOLO ID -> Name -> DB ID -> Display Name).
      - Geometric bounding box sanity bounds (rejects oversized hallucinations > 35% of frame).
      - Dual-engine ensemble: Pretrained COCO validation for robust Cell Phone (Class 67) & Person (Class 0)
        combined with Custom Retail weights (Biscuits, Lays, Mobile, Pen).
      - Strict confidence tiering: High (>=0.50) -> Valid Item; Medium (0.35-0.49) -> Uncertain; Low (<0.35) -> Dropped.
      - Startup banner diagnostics logging.
    """
    def __init__(self):
        self.model = None
        self.base_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_ready = False
        self.model_path = ""
        self.class_names = {}
        self.product_class_map = {}
        self.authoritative_mapping = {}
        self.coco_mappings = {}
        self.excluded_classes = set()

        self._load_authoritative_mapping()
        self._find_and_load_model()
        self._load_base_model()
        self._print_startup_diagnostics()

    def _load_authoritative_mapping(self):
        """Loads and activates the authoritative single-source-of-truth class mapping."""
        if os.path.exists(CLASS_MAPPING_FILE):
            try:
                with open(CLASS_MAPPING_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.authoritative_mapping = data.get("classes", {})
                    self.coco_mappings = data.get("coco_mappings", {})
                    self.excluded_classes = set(c.lower().strip() for c in data.get("excluded_classes", []))
                    
                    # Populate product class map
                    for cid_str, info in self.authoritative_mapping.items():
                        cid = int(cid_str)
                        self.product_class_map[cid] = info.get("db_product_name", info.get("model_class_name"))
                        self.class_names[cid] = info.get("model_class_name")
            except Exception as e:
                print(f"[YOLODetector] Error reading {CLASS_MAPPING_FILE}: {e}")

    def _find_and_load_model(self):
        """Locates the active or validated custom retail model weights."""
        target_path = None
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

        # 1. Check active_model.json
        active_json_path = os.path.join(workspace_root, "ml", "models", "active_model.json")
        if os.path.exists(active_json_path):
            try:
                with open(active_json_path, "r", encoding="utf-8") as f:
                    active_info = json.load(f)
                    m_path = active_info.get("model_path")
                    if m_path and os.path.exists(m_path):
                        target_path = os.path.abspath(m_path)
            except Exception as ex:
                print(f"[YOLODetector] Note reading active_model.json: {ex}")

        # 2. Priority check candidate paths
        if not target_path:
            possible_paths = [
                os.path.join(workspace_root, "ml", "models", "yolo11_smartshelf_v2", "best.pt"),
                os.path.join(workspace_root, "ml", "models", "yolo11_smartshelf_pen_lays_bisc", "best.pt"),
                os.path.join(workspace_root, "runs", "train", "yolo11_smartshelf_v2", "weights", "best.pt"),
                os.path.join(workspace_root, "backend", "yolo11n.pt"),
                os.path.join(workspace_root, "yolo11n.pt"),
                "yolo11n.pt"
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    target_path = os.path.abspath(p)
                    break

        if not target_path:
            target_path = "yolo11n.pt"

        self.model_path = target_path
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            self.model.to(self.device)
            # Sync names from loaded model if available
            if hasattr(self.model, "names") and self.model.names:
                for k, v in self.model.names.items():
                    if k not in self.class_names:
                        self.class_names[k] = v
            self.is_ready = True
        except Exception as e:
            print(f"[YOLODetector] Model initialization warning: {e}. Running base fallback.")
            self.is_ready = False

    def _load_base_model(self):
        """Loads base COCO model for high-precision Person and Cell Phone validation."""
        try:
            from ultralytics import YOLO
            workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
            base_candidates = [
                os.path.join(workspace_root, "backend", "yolo11n.pt"),
                os.path.join(workspace_root, "yolo11n.pt"),
                "yolo11n.pt"
            ]
            b_path = None
            for p in base_candidates:
                if os.path.exists(p):
                    b_path = p
                    break
            if not b_path:
                b_path = "yolo11n.pt"
            self.base_model = YOLO(b_path)
            self.base_model.to(self.device)
        except Exception as e:
            print(f"[YOLODetector] Note: Base COCO model initialization: {e}")

    def _print_startup_diagnostics(self):
        """Prints comprehensive model diagnostics banner at application startup."""
        conf_thresh = float(ai_config.get("detection_confidence", 0.45))
        model_name = os.path.basename(self.model_path) if self.model_path else "Uninitialized"
        print("\n==========================================================================")
        print("  SMARTSHELF COMPUTER VISION INFERENCE ENGINE INITIALIZED")
        print("==========================================================================")
        print(f"  MODEL PATH:            {self.model_path}")
        print(f"  MODEL TYPE:            YOLO11 (Ultralytics Transfer Architecture)")
        print(f"  MODEL VERSION:         v2.0 (Authoritative 18-Class Taxonomy)")
        print(f"  DEVICE ACCELERATION:   {self.device.upper()}")
        print(f"  CLASS COUNT:           {len(self.class_names)} configured classes")
        print(f"  CONFIDENCE THRESHOLD:  {conf_thresh}")
        print(f"  MAX OBJECT AREA RATIO: 35.0% of camera frame (Anti-Hallucination)")
        print(f"  MODEL CLASSES:         {dict(list(self.class_names.items())[:6])}...")
        print(f"  TARGET VALIDATION:     Biscuits (6), Pen (16), Lays (5), Cell Phone (12)")
        print("==========================================================================\n")

    def detect(self, frame: np.ndarray, conf_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Run inference on a single BGR OpenCV frame with anti-hallucination guards.
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]
        frame_area = float(max(1, w * h))
        conf = conf_threshold if conf_threshold is not None else float(ai_config.get("detection_confidence", 0.45))
        img_size = int(ai_config.get("input_size", 640))

        if not self.is_ready or self.model is None:
            return []

        detections = []
        has_cell_phone = False

        # ----------------------------------------------------------------------
        # 1. Base Pretrained COCO Pass (High Precision Cell Phone & Person)
        # ----------------------------------------------------------------------
        if self.base_model is not None:
            try:
                base_results = self.base_model(
                    frame,
                    imgsz=img_size,
                    conf=max(0.30, conf - 0.10),
                    device=self.device,
                    verbose=False
                )
                for br in base_results:
                    if br.boxes is None or len(br.boxes) == 0:
                        continue
                    for box in br.boxes:
                        cid = int(box.cls[0].item())
                        c_conf = float(box.conf[0].item())
                        xyxy = [int(x) for x in box.xyxy[0].tolist()]
                        b_area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])
                        b_ratio = b_area / frame_area

                        # Person detection (COCO 0)
                        if cid == 0:
                            detections.append({
                                "class_id": 999,
                                "label": "Person",
                                "display_name": "Person",
                                "category": "person",
                                "confidence": round(c_conf, 3),
                                "box": xyxy,
                                "track_id": None,
                                "db_product_id": None
                            })

                        # Cell Phone detection (COCO 67)
                        elif cid == 67 and b_ratio <= 0.35:
                            has_cell_phone = True
                            detections.append({
                                "class_id": 12,
                                "label": "Mobile Phone",
                                "display_name": "Cell Phone",
                                "category": "item",
                                "confidence": round(c_conf, 3),
                                "box": xyxy,
                                "track_id": None,
                                "db_product_id": 11
                            })
            except Exception as b_err:
                pass

        # ----------------------------------------------------------------------
        # 2. Custom Retail Model Inference (Biscuits, Lays, Mobile, Pen, etc.)
        # ----------------------------------------------------------------------
        try:
            results = self.model(
                frame,
                imgsz=img_size,
                conf=0.35,  # Capture medium and high confidence for tiering
                device=self.device,
                verbose=False
            )
        except Exception as e:
            print(f"[YOLODetector] Custom model inference error: {e}")
            return detections

        for r in results:
            if r.boxes is None or len(r.boxes) == 0:
                continue

            for box in r.boxes:
                cls_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                xyxy = [int(x) for x in box.xyxy[0].tolist()]

                # Geometric sanity checks
                box_w = xyxy[2] - xyxy[0]
                box_h = xyxy[3] - xyxy[1]
                box_area = box_w * box_h
                area_ratio = box_area / frame_area

                # Reject tiny noise artifacts
                if box_w < 15 or box_h < 15:
                    continue

                raw_name = self.class_names.get(cls_id, f"class_{cls_id}")
                norm_raw = raw_name.lower().replace("_", " ").strip()

                # Filter excluded furniture / clothing classes
                if norm_raw in self.excluded_classes:
                    continue

                # Anti-Hallucination Guard: Reject oversized product bounding boxes
                # A retail packaged item (chips, phone, biscuits, pen) never covers > 35% of frame
                if area_ratio > 0.35:
                    continue

                # Resolve via authoritative mapping
                mapping_info = self.authoritative_mapping.get(str(cls_id), {})
                db_name = mapping_info.get("db_product_name", self.product_class_map.get(cls_id, raw_name))
                disp_name = mapping_info.get("display_name", raw_name)
                db_id = mapping_info.get("db_product_id", None)
                cat = mapping_info.get("category", "item")

                # Mobile / Cell Phone handling
                if cls_id == 12 or norm_raw in ["mobile", "cell phone", "phone", "cellphone"]:
                    has_cell_phone = True
                    disp_name = "Cell Phone"
                    db_name = "Mobile Phone"
                    db_id = 11
                    cls_id = 12

                # CRITICAL GUARD: Suppress false Lays predictions
                # If a cell phone is in the scene and Lays has low/medium confidence (<0.65), drop the fake Lays!
                if cls_id == 5 or norm_raw == "lays":
                    if has_cell_phone and confidence < 0.65:
                        continue
                    # Also if Lays confidence is marginal on textured background, drop it
                    if confidence < 0.48:
                        continue

                # Check if this detection duplicates an existing COCO cell phone detection
                if cls_id == 12:
                    already_detected = False
                    for d in detections:
                        if d["class_id"] == 12:
                            # Check overlap (IoU)
                            dx1, dy1, dx2, dy2 = d["box"]
                            ix1 = max(xyxy[0], dx1)
                            iy1 = max(xyxy[1], dy1)
                            ix2 = min(xyxy[2], dx2)
                            iy2 = min(xyxy[3], dy2)
                            if ix2 > ix1 and iy2 > iy1:
                                inter = (ix2 - ix1) * (iy2 - iy1)
                                union = box_area + (dx2 - dx1) * (dy2 - dy1) - inter
                                if inter / float(max(1, union)) > 0.25:
                                    already_detected = True
                                    # Update confidence if higher
                                    if confidence > d["confidence"]:
                                        d["confidence"] = round(confidence, 3)
                                        d["box"] = xyxy
                                    break
                    if already_detected:
                        continue

                # Strict Confidence Tiering
                if confidence >= 0.50:
                    final_category = cat
                    final_label = db_name
                elif confidence >= 0.35:
                    final_category = "uncertain"
                    final_label = f"Uncertain: {disp_name}"
                else:
                    continue

                detections.append({
                    "class_id": cls_id,
                    "label": final_label,
                    "display_name": disp_name,
                    "category": final_category,
                    "confidence": round(confidence, 3),
                    "box": xyxy,
                    "track_id": None,
                    "db_product_id": db_id
                })

        return detections

    def get_info(self) -> Dict[str, Any]:
        return {
            "model_path": self.model_path,
            "model_name": os.path.basename(self.model_path) if self.model_path else "YOLO",
            "device": self.device.upper(),
            "is_ready": self.is_ready,
            "classes_count": len(self.class_names),
            "mapped_classes": len(self.product_class_map)
        }

    def get_diagnostics(self) -> Dict[str, Any]:
        """Provides full model health and diagnostic state for API endpoints and debug HUD."""
        return {
            "active_model_path": self.model_path,
            "active_model_name": os.path.basename(self.model_path) if self.model_path else "YOLO11",
            "model_type": "YOLO11s/n Dual-Engine Ensemble",
            "model_version": "v2.0-Production",
            "device": self.device.upper(),
            "confidence_threshold": float(ai_config.get("detection_confidence", 0.45)),
            "max_object_area_ratio": 0.35,
            "class_count": len(self.class_names),
            "classes": self.class_names,
            "authoritative_mapping_version": "2.0.0",
            "key_classes": {
                "0": "Apple",
                "5": "Lays Chips",
                "6": "Biscuits",
                "12": "Cell Phone",
                "16": "Pen"
            },
            "is_ready": self.is_ready
        }

detector = YOLODetector()
