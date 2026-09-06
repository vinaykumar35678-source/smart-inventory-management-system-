import os
import cv2
import torch
import numpy as np
from typing import List, Dict, Any, Optional
from ..config.config import ai_config

class YOLODetector:
    """
    Object Detector powered by Ultralytics YOLO.
    Supports YOLOv8 / YOLO11 with automatic hardware acceleration (CUDA vs. CPU),
    configurable confidence thresholds, dynamic class-to-product mapping, and fallback modes.
    """
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_ready = False
        self.model_path = ""
        self.class_names = {}
        # Dynamic mapping from model class_id -> DB product name / ID
        self.product_class_map = {}
        self._find_and_load_model()

    def _find_and_load_model(self):
        primary_model = ai_config.get("primary_model", "yolo11n.pt")
        possible_paths = [
            primary_model,
            "yolo11n.pt",
            "yolo11s.pt",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "smart_shelf", "runs", "detect", "smart_shelf_model", "weights", "best.pt"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "smart_shelf", "yolo11n.pt"),
            os.path.join(os.path.dirname(__file__), "..", "..", "yolov8n.pt"),
            "yolov8n.pt"
        ]

        target_path = None
        for p in possible_paths:
            if os.path.exists(p):
                target_path = os.path.abspath(p)
                break

        if not target_path:
            target_path = primary_model

        self.model_path = target_path
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            # Move to device
            self.model.to(self.device)
            self.class_names = self.model.names if hasattr(self.model, "names") else {}
            self.is_ready = True
            print(f"[YOLODetector] Loaded model '{os.path.basename(self.model_path)}' on device: {self.device.upper()}")
        except Exception as e:
            print(f"[YOLODetector] Model initialization warning: {e}. Will operate in fallback mode.")
            self.is_ready = False

    def update_class_mapping(self, mapping: Dict[int, str]):
        """
        Configure mapping from model class_id -> product_name or DB product.
        Allows custom classes without retraining the underlying model.
        """
        self.product_class_map.update(mapping)

    def switch_model(self, model_path: str, class_map: Optional[Dict[Any, str]] = None):
        """
        Dynamically hot-reload model weights and class mappings at runtime.
        Integrates custom trained models into the active detection pipeline.
        """
        from ultralytics import YOLO
        try:
            print(f"[YOLODetector] Switching model to: {model_path}")
            new_model = YOLO(model_path)
            new_model.to(self.device)
            self.model = new_model
            self.model_path = model_path
            self.class_names = self.model.names if hasattr(self.model, "names") else {}
            if class_map:
                formatted_map = {int(k): str(v) for k, v in class_map.items()}
                self.product_class_map.update(formatted_map)
            self.is_ready = True
            print(f"[YOLODetector] Successfully activated model '{os.path.basename(model_path)}' ({len(self.class_names)} classes).")
            return True
        except Exception as e:
            print(f"[YOLODetector ERROR] Failed to switch model to {model_path}: {e}")
            raise e

    def detect(self, frame: np.ndarray, conf_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Run inference on a single BGR OpenCV frame.
        Returns a list of standardized detections:
        [
            {
                "class_id": int,
                "label": str,
                "category": "person" | "item" | "shelf" | "cart",
                "confidence": float,
                "box": [x1, y1, x2, y2],
                "track_id": None
            }, ...
        ]
        """
        if frame is None or frame.size == 0:
            return []

        conf = conf_threshold if conf_threshold is not None else float(ai_config.get("detection_confidence", 0.40))
        img_size = int(ai_config.get("input_size", 640))

        if not self.is_ready or self.model is None:
            return self._fallback_detect(frame)

        try:
            results = self.model(
                frame,
                imgsz=img_size,
                conf=conf,
                device=self.device,
                verbose=False
            )
        except Exception as e:
            print(f"[YOLODetector] Inference error: {e}")
            return self._fallback_detect(frame)

        detections = []
        for r in results:
            if r.boxes is None or len(r.boxes) == 0:
                continue

            for box in r.boxes:
                cls_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                xyxy = [int(x) for x in box.xyxy[0].tolist()]

                raw_name = self.class_names.get(cls_id, f"class_{cls_id}")
                
                # Check custom mapping first
                if cls_id in self.product_class_map:
                    label = self.product_class_map[cls_id]
                    category = "item"
                elif raw_name.lower() == "person":
                    label = "Person"
                    category = "person"
                elif "shelf" in raw_name.lower() or "rack" in raw_name.lower():
                    label = "Shelf"
                    category = "shelf"
                elif "cart" in raw_name.lower() or "basket" in raw_name.lower():
                    label = "Shopping Cart"
                    category = "cart"
                else:
                    # Generic inventory item (e.g. bottle, apple, banana, book, cell phone)
                    label = raw_name.replace("_", " ").title()
                    category = "item"

                detections.append({
                    "class_id": cls_id,
                    "label": label,
                    "category": category,
                    "confidence": round(confidence, 3),
                    "box": xyxy,
                    "track_id": None
                })

        return detections

    def _fallback_detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Non-destructive fallback simulation when YOLO is uninitialized."""
        return []

    def get_info(self) -> Dict[str, Any]:
        return {
            "model_path": self.model_path,
            "model_name": os.path.basename(self.model_path) if self.model_path else "YOLO",
            "device": self.device.upper(),
            "is_ready": self.is_ready,
            "classes_count": len(self.class_names),
            "mapped_classes": len(self.product_class_map)
        }

detector = YOLODetector()
