import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "thresholds.json")

DEFAULT_CONFIG = {
    # Model configuration
    "primary_model": "yolo11n.pt",
    "fallback_model": "yolov8n.pt",
    "model_name": "yolo11n.pt",
    "detection_confidence": 0.45,
    "iou_threshold": 0.45,
    "input_size": 640,
    "frame_skip": 1,
    "pose_enabled": True,

    # Object Tracking configuration
    "tracker": "bytetrack",
    "lost_grace_frames": 20,       # Frames a missing product is held in TEMPORARILY_OCCLUDED before being marked LOST
    "max_track_age": 30,           # Maximum frames to keep lost tracks in memory
    "track_history_len": 30,       # Centroid trajectory deque length

    # Spatial Shelf configuration
    "shelf_exit_margin": 20,       # Pixels margin outside shelf boundary before considering removal
    "spatial_rule": "center_point", # Associating items by bounding box center point

    # Inventory State Machine configuration
    "min_track_age": 10,           # Stable frames required to transition NEW -> STABLE_ON_SHELF
    "min_movement_distance": 30.0, # Minimum pixel distance an item must move from its shelf baseline
    "removal_confirmation_frames": 15, # Continuous frames outside shelf required for REMOVAL_CONFIRMED
    "removal_confirmation_time": 1.0,  # Minimum seconds outside shelf
    "placement_confirmation_frames": 15, # Continuous frames inside shelf required for PLACEMENT_CONFIRMED
    "event_cooldown_seconds": 2.0,      # Cooldown before the same track can generate another event
    "debounce_seconds": 2.5,
    "suspicious_score_threshold": 70,
    "initialization_seconds": 5.0,      # Startup baseline aggregation window
    "temporal_smoothing_window": 7      # Window for rolling median shelf count smoothing
}

class AIConfig:
    def __init__(self):
        self._config = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                    self._config.update(saved)
            except Exception as e:
                print(f"[AIConfig] Error loading {CONFIG_FILE}: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"[AIConfig] Error saving {CONFIG_FILE}: {e}")

    def get(self, key, default=None):
        return self._config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def update(self, new_values: dict):
        for k, v in new_values.items():
            if k in DEFAULT_CONFIG:
                val_type = type(DEFAULT_CONFIG[k])
                try:
                    self._config[k] = val_type(v)
                except Exception:
                    self._config[k] = v
            else:
                self._config[k] = v
        self.save()

    def as_dict(self):
        return dict(self._config)

ai_config = AIConfig()
