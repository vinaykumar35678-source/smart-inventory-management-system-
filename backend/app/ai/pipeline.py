import time
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from .config.config import ai_config
from .detection.detector import detector
from .tracking.tracker import tracker
from .pose.pose_estimator import pose_estimator
from .inventory.shelf_monitor import shelf_monitor
from .behavior.behavior_analyzer import behavior_analyzer
from .events.event_engine import event_engine

class VisionPipeline:
    """
    Main Computer Vision and Loss Prevention Pipeline Coordinator.
    Orchestrates:
      Video Frame -> YOLO Detection -> ByteTrack -> Pose Estimation ->
      Shelf/Zone Monitor -> Temporal Behavior -> Event Engine -> Database -> WebSocket
    """
    def __init__(self):
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0
        self.last_inference_ms = 0.0
        self.is_running = True
        self.active_camera = "Webcam 0"

    def process_frame(self, frame: np.ndarray, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Executes the end-to-end computer vision pipeline on a single video frame.
        """
        if frame is None or frame.size == 0:
            return {
                "tracked_objects": [],
                "shelves": {},
                "pose_results": [],
                "events": [],
                "fps": self.current_fps,
                "latency_ms": self.last_inference_ms
            }

        start_time = time.time()
        self.frame_count += 1
        h, w = frame.shape[:2]

        # 1. Update shelf configurations if db session is available
        if db:
            from .. import models
            shelves = db.query(models.Shelf).all()
            if shelves:
                shelf_monitor.set_shelves_from_db(shelves)

        # 2. Object Detection (YOLO)
        raw_detections = detector.detect(frame)

        # 3. Object Tracking (ByteTrack)
        tracked_objects = tracker.update(raw_detections)

        # 4. Pose Estimation & Interaction
        person_tracks = [t for t in tracked_objects if t["category"] == "person"]
        shelf_boxes = shelf_monitor.get_pixel_boxes(w, h)
        pose_results = pose_estimator.estimate(frame, person_tracks, shelf_boxes)

        # 5. Shelf / Zone Spatial Evaluation & Misplaced Detection
        shelf_eval = shelf_monitor.evaluate(tracked_objects, w, h)

        # 6. Temporal Behavior & Loss Prevention Scoring
        events = behavior_analyzer.analyze_frame(tracked_objects, shelf_eval, pose_results)

        # 7. Persist Events to Database if db is provided
        processed_events = []
        if db and events:
            for ev in events:
                result = event_engine.process_event(ev, db)
                processed_events.append(result)
        else:
            processed_events = events

        # Performance metrics
        elapsed = time.time() - start_time
        self.last_inference_ms = round(elapsed * 1000, 1)

        if time.time() - self.last_fps_time >= 1.0:
            self.current_fps = round(self.frame_count / max(0.001, time.time() - self.last_fps_time), 1)
            self.frame_count = 0
            self.last_fps_time = time.time()

        # Determine overall inventory monitoring status
        pending = behavior_analyzer.get_pending_summary()
        tracked_items_count = len([t for t in tracked_objects if t.get("category") != "person"])
        
        system_status = "NORMAL"
        if pending.get("pending_removals_count", 0) > 0:
            system_status = "POSSIBLE_REMOVAL"
        elif pending.get("pending_placements_count", 0) > 0:
            system_status = "POSSIBLE_PLACEMENT"

        return {
            "frame_width": w,
            "frame_height": h,
            "tracked_objects": tracked_objects,
            "tracked_count": tracked_items_count,
            "shelves": shelf_eval["shelves"],
            "misplaced_items": shelf_eval["misplaced_items"],
            "pose_results": pose_results,
            "events": processed_events,
            "pending_events": pending["pending_removals_count"] + pending["pending_placements_count"],
            "system_status": system_status,
            "fps": self.current_fps if self.current_fps > 0 else round(1.0 / max(0.001, elapsed), 1),
            "latency_ms": self.last_inference_ms,
            "device": detector.device.upper(),
            "model_name": detector.get_info()["model_name"]
        }

    def reset(self):
        tracker.reset()
        behavior_analyzer.reset()
        self.frame_count = 0

pipeline = VisionPipeline()
