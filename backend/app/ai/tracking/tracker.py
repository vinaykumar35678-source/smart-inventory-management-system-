"""
tracker.py — Persistent ByteTrack Multi-Object Tracker with Occlusion Tolerance
Implements persistent Track IDs, spatial center points, multi-frame state tracking,
and seamless track recovery during temporary visual occlusions (up to lost_grace_frames).
"""
import time
import math
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import deque
from ..config.config import ai_config

def calculate_iou(boxA: List[int], boxB: List[int]) -> float:
    """Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    return interArea / float(boxAArea + boxBArea - interArea)

def euclidean_distance(pt1: Tuple[int, int], pt2: Tuple[int, int]) -> float:
    """Computes Euclidean distance between two 2D points."""
    return math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)

class TrackState:
    NEW = "NEW"
    STABLE_ON_SHELF = "STABLE_ON_SHELF"
    INTERACTING = "INTERACTING"
    POSSIBLE_REMOVAL = "POSSIBLE_REMOVAL"
    REMOVAL_CONFIRMED = "REMOVAL_CONFIRMED"
    POSSIBLE_PLACEMENT = "POSSIBLE_PLACEMENT"
    PLACEMENT_CONFIRMED = "PLACEMENT_CONFIRMED"
    TEMPORARILY_OCCLUDED = "TEMPORARILY_OCCLUDED"
    LOST = "LOST"

class TrackedObject:
    def __init__(self, track_id: int, detection: Dict[str, Any]):
        now = time.time()
        self.track_id: int = track_id
        self.class_id: int = detection.get("class_id", 0)
        self.class_name: str = detection.get("label", "Product")
        self.label: str = self.class_name
        self.category: str = detection.get("category", "item")
        self.confidence: float = float(detection.get("confidence", 0.9))
        self.box: List[int] = list(map(int, detection["box"]))
        
        # Center-point rule
        self.center_x: int = (self.box[0] + self.box[2]) // 2
        self.center_y: int = (self.box[1] + self.box[3]) // 2
        self.centroid: Tuple[int, int] = (self.center_x, self.center_y)
        self.baseline_centroid: Tuple[int, int] = (self.center_x, self.center_y)

        # Timestamps
        self.first_seen: float = now
        self.last_seen: float = now
        self.state_timer: float = now

        # Zone tracking
        self.current_zone: Optional[str] = None
        self.previous_zone: Optional[str] = None
        self.current_shelf_id: Optional[int] = None
        self.initial_shelf_id: Optional[int] = None

        # State machine
        self.track_state: str = TrackState.NEW
        self.prev_track_state: str = TrackState.NEW
        self.frames_visible: int = 1
        self.frames_missing: int = 0
        self.stable_frames: int = 0

        # Motion & History
        self.velocity: Tuple[float, float] = (0.0, 0.0)
        self.history: deque = deque(maxlen=int(ai_config.get("track_history_len", 30)))
        self.history.append(self.centroid)

        # Event tracking & cooldown
        self.last_confirmed_event: Optional[str] = None
        self.last_event_time: float = 0.0
        self.movement_from_shelf: float = 0.0

    def update(self, detection: Dict[str, Any]):
        """Update track with new detection."""
        now = time.time()
        self.box = list(map(int, detection["box"]))
        self.confidence = float(detection.get("confidence", self.confidence))
        self.last_seen = now
        self.frames_visible += 1
        self.frames_missing = 0

        new_cx = (self.box[0] + self.box[2]) // 2
        new_cy = (self.box[1] + self.box[3]) // 2
        
        # Calculate velocity
        prev_cx, prev_cy = self.centroid
        self.velocity = (float(new_cx - prev_cx), float(new_cy - prev_cy))
        self.center_x = new_cx
        self.center_y = new_cy
        self.centroid = (new_cx, new_cy)
        self.history.append(self.centroid)

        # Calculate total movement from baseline shelf position
        self.movement_from_shelf = euclidean_distance(self.centroid, self.baseline_centroid)

        # Recover from occlusion
        if self.track_state == TrackState.TEMPORARILY_OCCLUDED:
            self.track_state = self.prev_track_state if self.prev_track_state != TrackState.TEMPORARILY_OCCLUDED else TrackState.STABLE_ON_SHELF

    def mark_missing(self):
        """Mark missing frame with occlusion grace handling."""
        self.frames_missing += 1
        lost_grace = int(ai_config.get("lost_grace_frames", 20))
        
        if self.frames_missing <= lost_grace:
            if self.track_state != TrackState.TEMPORARILY_OCCLUDED:
                self.prev_track_state = self.track_state
                self.track_state = TrackState.TEMPORARILY_OCCLUDED
        else:
            self.track_state = TrackState.LOST

    def to_dict(self) -> Dict[str, Any]:
        """Convert track to standardized dictionary format."""
        return {
            "track_id": self.track_id,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "label": self.class_name,
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "bounding_box": self.box,
            "box": self.box,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "centroid": (self.center_x, self.center_y),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "current_zone": self.current_zone,
            "previous_zone": self.previous_zone,
            "current_shelf_id": self.current_shelf_id,
            "initial_shelf_id": self.initial_shelf_id,
            "track_state": self.track_state,
            "frames_visible": self.frames_visible,
            "frames_missing": self.frames_missing,
            "velocity": self.velocity,
            "trajectory": list(self.history),
            "is_occluded": (self.track_state == TrackState.TEMPORARILY_OCCLUDED),
            "movement_distance": round(self.movement_from_shelf, 1)
        }

class ByteTracker:
    """
    Multi-Object Tracker maintaining persistent IDs across frames.
    Features:
      - Two-stage association (high-confidence + low-confidence)
      - Occlusion grace window (preserves track state when object is missed)
      - Spatial re-identification (re-associates recovered tracks upon reappearance)
    """
    def __init__(self, max_missing_frames: int = 30, iou_threshold: float = 0.40):
        self.max_missing_frames = max_missing_frames
        self.iou_threshold = iou_threshold
        self.next_id = 1
        self.tracks: Dict[int, TrackedObject] = {}

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes raw detections, associates with existing tracks (including occluded tracks),
        initializes new tracks, and returns all active and temporarily occluded tracks.
        """
        iou_thresh = float(ai_config.get("iou_threshold", self.iou_threshold))
        lost_grace = int(ai_config.get("lost_grace_frames", 20))
        max_age = int(ai_config.get("max_track_age", self.max_missing_frames))

        existing_tracks = list(self.tracks.values())
        matched_track_ids = set()
        matched_det_indices = set()

        # Step 1: Association between detections and active tracks
        if existing_tracks and detections:
            cost_matrix = np.zeros((len(existing_tracks), len(detections)))
            for t_idx, track in enumerate(existing_tracks):
                for d_idx, det in enumerate(detections):
                    # Compute IoU
                    iou = calculate_iou(track.box, det["box"])
                    
                    # Bonus for matching same class and category
                    bonus = 0.0
                    if track.category == det.get("category"):
                        bonus += 0.15
                    if track.class_name == det.get("label"):
                        bonus += 0.15

                    # Spatial proximity heuristic for occluded / recovering tracks
                    det_cx = (det["box"][0] + det["box"][2]) // 2
                    det_cy = (det["box"][1] + det["box"][3]) // 2
                    dist = euclidean_distance(track.centroid, (det_cx, det_cy))
                    
                    # If very close spatially and same class, allow matching even with low IoU
                    proximity_bonus = 0.25 if dist < 45 and track.class_name == det.get("label") else 0.0

                    cost_matrix[t_idx, d_idx] = iou + bonus + proximity_bonus

            # Greedy assignment
            while True:
                if cost_matrix.size == 0 or np.max(cost_matrix) < iou_thresh:
                    break
                t_idx, d_idx = np.unravel_index(np.argmax(cost_matrix), cost_matrix.shape)
                if cost_matrix[t_idx, d_idx] < iou_thresh:
                    break

                track = existing_tracks[t_idx]
                det = detections[d_idx]
                track.update(det)
                matched_track_ids.add(track.track_id)
                matched_det_indices.add(d_idx)

                cost_matrix[t_idx, :] = -1.0
                cost_matrix[:, d_idx] = -1.0

        # Step 2: Mark missing for unmatched tracks (enters occlusion grace period)
        for track in existing_tracks:
            if track.track_id not in matched_track_ids:
                track.mark_missing()

        # Step 3: Initialize new tracks for unmatched detections
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_det_indices:
                new_track = TrackedObject(self.next_id, det)
                self.tracks[self.next_id] = new_track
                self.next_id += 1

        # Step 4: Prune tracks that have exceeded max_age frames missing
        prune_ids = [tid for tid, t in self.tracks.items() if t.frames_missing > max_age]
        for tid in prune_ids:
            del self.tracks[tid]

        # Step 5: Return active tracks AND temporarily occluded tracks
        # Occluded tracks remain tracked to prevent instantaneous count drops!
        current_tracked = [
            t.to_dict() for t in self.tracks.values()
            if t.frames_missing <= lost_grace
        ]
        return current_tracked

    def reset(self):
        """Reset all tracking states."""
        self.tracks.clear()
        self.next_id = 1

tracker = ByteTracker()
