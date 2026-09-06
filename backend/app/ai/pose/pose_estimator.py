import os
import torch
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

class PoseEstimator:
    """
    Human Pose Estimator using YOLO Pose (COCO 17 Keypoints).
    Detects upper body posture, arm extension, and wrist coordinates to analyze
    reaching behaviors and hand-product interactions near shelves.
    Provides algorithmic spatial heuristics when pose weights are unavailable.
    """
    # COCO Keypoint indexes:
    # 5: Left Shoulder, 6: Right Shoulder
    # 7: Left Elbow,    8: Right Elbow
    # 9: Left Wrist,    10: Right Wrist
    WRIST_LEFT = 9
    WRIST_RIGHT = 10
    SHOULDER_LEFT = 5
    SHOULDER_RIGHT = 6

    def __init__(self):
        self.model = None
        self.is_ready = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._init_model()

    def _init_model(self):
        try:
            from ultralytics import YOLO
            # Try to load lightweight YOLOv8 nano pose model
            model_path = os.path.join(os.path.dirname(__file__), "yolov8n-pose.pt")
            if not os.path.exists(model_path):
                model_path = "yolov8n-pose.pt"
            
            self.model = YOLO(model_path)
            self.model.to(self.device)
            self.is_ready = True
            print("[PoseEstimator] YOLO-Pose model loaded successfully.")
        except Exception as e:
            print(f"[PoseEstimator] Note: YOLO-Pose model unavailable ({e}). Using spatial geometric pose heuristics.")
            self.is_ready = False

    def estimate(self, frame: np.ndarray, person_tracks: List[Dict[str, Any]], shelf_rois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes detected person tracks and calculates reaching/interaction status with shelf ROIs.
        """
        pose_results = []
        if frame is None or frame.size == 0 or not person_tracks:
            return pose_results

        # If YOLO-Pose model is available, run inference on the frame
        keypoints_by_box = {}
        if self.is_ready and self.model is not None:
            try:
                results = self.model(frame, imgsz=320, conf=0.4, device=self.device, verbose=False)
                for r in results:
                    if r.keypoints is not None and len(r.keypoints.xy) > 0:
                        for idx, kpts in enumerate(r.keypoints.xy):
                            if idx < len(r.boxes):
                                box = [int(x) for x in r.boxes.xyxy[idx].tolist()]
                                keypoints_by_box[tuple(box[:2])] = kpts.cpu().numpy()
            except Exception as e:
                pass

        for person in person_tracks:
            box = person["box"]
            track_id = person["track_id"]
            p_center = person["centroid"]
            
            has_real_pose = False
            kpts_data = []
            left_wrist = None
            right_wrist = None

            # Find matching keypoints for this person
            for (bx, by), kpts in keypoints_by_box.items():
                if abs(bx - box[0]) < 60 and abs(by - box[1]) < 60:
                    has_real_pose = True
                    kpts_data = kpts.tolist()
                    if len(kpts) > self.WRIST_RIGHT:
                        lw = kpts[self.WRIST_LEFT]
                        rw = kpts[self.WRIST_RIGHT]
                        if lw[0] > 0 and lw[1] > 0:
                            left_wrist = (int(lw[0]), int(lw[1]))
                        if rw[0] > 0 and rw[1] > 0:
                            right_wrist = (int(rw[0]), int(rw[1]))
                    break

            # If real pose keypoints weren't found, estimate hand positions geometrically from bounding box
            if not has_real_pose:
                # Geometric approximation: arms usually extend from upper-middle half of person box
                w = box[2] - box[0]
                h = box[3] - box[1]
                # Default hand estimates at mid-height
                left_wrist = (box[0] + int(w * 0.25), box[1] + int(h * 0.55))
                right_wrist = (box[0] + int(w * 0.75), box[1] + int(h * 0.55))

            # Check if either hand or person center is reaching into or near any shelf ROI
            is_reaching = False
            interacting_shelf_id = None
            min_shelf_dist = 9999.0

            for shelf in shelf_rois:
                # Calculate distance between hands / person and shelf box
                s_box = shelf["box"]  # [x1, y1, x2, y2]
                
                # Check if wrist is inside or very close (<40px) to shelf
                for wrist in [left_wrist, right_wrist]:
                    if wrist:
                        if (s_box[0] - 40 <= wrist[0] <= s_box[2] + 40 and 
                            s_box[1] - 40 <= wrist[1] <= s_box[3] + 40):
                            is_reaching = True
                            interacting_shelf_id = shelf.get("id")
                            break
                
                # Also check general person-shelf proximity
                s_cx = (s_box[0] + s_box[2]) // 2
                s_cy = (s_box[1] + s_box[3]) // 2
                dist = np.sqrt((p_center[0] - s_cx)**2 + (p_center[1] - s_cy)**2)
                if dist < min_shelf_dist:
                    min_shelf_dist = dist
                    if not is_reaching and dist < 120:
                        is_reaching = True
                        interacting_shelf_id = shelf.get("id")

            pose_results.append({
                "person_track_id": track_id,
                "box": box,
                "has_real_pose": has_real_pose,
                "keypoints": kpts_data,
                "left_wrist": left_wrist,
                "right_wrist": right_wrist,
                "is_reaching": is_reaching,
                "interacting_shelf_id": interacting_shelf_id,
                "shelf_distance": round(min_shelf_dist, 1)
            })

        return pose_results

pose_estimator = PoseEstimator()
