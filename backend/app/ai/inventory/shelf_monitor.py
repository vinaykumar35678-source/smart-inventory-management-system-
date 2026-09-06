"""
shelf_monitor.py — Virtual Shelf & ROI Zone Evaluation Engine
Implements:
  - Bounding box center-point spatial containment with configurable shelf_exit_margin
  - Occlusion-aware presence holding (holds occluded items during grace period)
  - Temporal smoothing (rolling window median/mode) to eliminate visual count flickering
  - Misplaced product detection via category compatibility rules
"""
import statistics
from typing import List, Dict, Any, Optional
from collections import defaultdict, deque
from ..config.config import ai_config

class ShelfMonitor:
    """
    Virtual Shelf and Zone Monitoring Engine.
    Evaluates product centroids against shelf ROI zones with exit margins and temporal smoothing.
    """
    def __init__(self):
        self.shelves: Dict[int, Dict[str, Any]] = {}
        # Historical count buffer for rolling median smoothing: {shelf_id: deque(maxlen=7)}
        self.count_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=int(ai_config.get("temporal_smoothing_window", 7))))
        
        # Product-to-shelf compatibility mapping
        self.category_rules: Dict[str, str] = {
            "Milk (1L)": "Dairy",
            "Eggs (12)": "Dairy",
            "Apple": "Fruits",
            "Banana": "Fruits",
            "Orange": "Fruits",
            "Carrot": "Vegetables",
            "Mobile Phone": "Electronics",
            "Calculator": "Electronics",
            "Book": "Stationery",
            "Pen": "Stationery",
            "Paper Ream": "Stationery",
            "Water Bottle": "Beverages",
            "Lays": "Snacks",
            "Biscuits": "Snacks",
            "Bread": "Bakery"
        }

    def set_shelves_from_db(self, db_shelves: List[Any]):
        """Populate virtual shelf configurations from database models."""
        self.shelves.clear()
        for s in db_shelves:
            self.shelves[s.id] = {
                "id": s.id,
                "name": s.name,
                "category": s.category or "General",
                "roi_x1": float(s.roi_x1),
                "roi_y1": float(s.roi_y1),
                "roi_x2": float(s.roi_x2),
                "roi_y2": float(s.roi_y2),
                "capacity": s.capacity or 20,
                "current_count": s.current_count or 0,
                "status": s.status or "NORMAL"
            }

    def get_pixel_boxes(self, frame_w: int, frame_h: int) -> List[Dict[str, Any]]:
        """Converts normalized ROI coordinates (0.0 to 1.0) into pixel boxes for a given frame."""
        boxes = []
        for sid, s in self.shelves.items():
            x1 = int(s["roi_x1"] * frame_w)
            y1 = int(s["roi_y1"] * frame_h)
            x2 = int(s["roi_x2"] * frame_w)
            y2 = int(s["roi_y2"] * frame_h)
            boxes.append({
                "id": sid,
                "name": s["name"],
                "category": s["category"],
                "capacity": s["capacity"],
                "box": [x1, y1, x2, y2]
            })
        return boxes

    def evaluate(self, tracked_items: List[Dict[str, Any]], frame_w: int, frame_h: int) -> Dict[str, Any]:
        """
        Evaluates which items are inside each shelf ROI using center-point containment and margins.
        Includes occluded items currently in grace period to prevent count flickering.
        Computes rolling median smoothed counts.
        """
        shelf_boxes = self.get_pixel_boxes(frame_w, frame_h)
        margin = int(ai_config.get("shelf_exit_margin", 20))
        
        # Initialize shelf states
        shelf_states = {}
        for s in shelf_boxes:
            shelf_states[s["id"]] = {
                "id": s["id"],
                "name": s["name"],
                "category": s["category"],
                "capacity": s["capacity"],
                "box": s["box"],
                "items": [],
                "item_counts": {},
                "detected_count": 0,
                "smoothed_count": 0,
                "pending_removals": 0,
                "pending_placements": 0,
                "difference": 0,
                "is_empty": True,
                "status": "NORMAL"
            }

        misplaced_items = []
        unassigned_items = []

        # Evaluate each tracked product item
        for item in tracked_items:
            if item.get("category") == "person":
                continue

            # Robust center-point coordinates
            cx = item.get("center_x") or item["centroid"][0]
            cy = item.get("center_y") or item["centroid"][1]
            
            assigned_shelf_id = None

            # Check center-point containment in each shelf ROI (with boundary tolerance margin)
            for s in shelf_boxes:
                sx1, sy1, sx2, sy2 = s["box"]
                # Expanded boundary using shelf_exit_margin
                if (sx1 - margin) <= cx <= (sx2 + margin) and (sy1 - margin) <= cy <= (sy2 + margin):
                    assigned_shelf_id = s["id"]
                    shelf_states[assigned_shelf_id]["items"].append(item)
                    item["current_shelf_id"] = assigned_shelf_id
                    item["current_zone"] = s["name"]
                    
                    # Tally item counts
                    lbl = item["label"]
                    shelf_states[assigned_shelf_id]["item_counts"][lbl] = (
                        shelf_states[assigned_shelf_id]["item_counts"].get(lbl, 0) + 1
                    )

                    # Check for misplaced product
                    expected_category = self.category_rules.get(lbl)
                    if expected_category and expected_category.lower() != s["category"].lower() and s["category"].lower() != "general":
                        misplaced_items.append({
                            "track_id": item["track_id"],
                            "product": lbl,
                            "detected_shelf": s["name"],
                            "detected_category": s["category"],
                            "expected_category": expected_category,
                            "box": item["box"],
                            "confidence": item["confidence"]
                        })
                    break

            if not assigned_shelf_id:
                item["current_shelf_id"] = None
                unassigned_items.append(item)

        # Temporal smoothing & status assignment
        window_size = int(ai_config.get("temporal_smoothing_window", 7))
        for sid, sinfo in shelf_states.items():
            raw_count = len(sinfo["items"])
            sinfo["detected_count"] = raw_count
            
            # Append to rolling history
            hist = self.count_history[sid]
            hist.append(raw_count)
            
            # Compute rolling median to prevent count flickering
            smoothed_val = int(statistics.median(list(hist)))
            sinfo["smoothed_count"] = smoothed_val
            sinfo["is_empty"] = (smoothed_val == 0)
            
            # Count pending state machine events
            for it in sinfo["items"]:
                tstate = it.get("track_state")
                if tstate == "POSSIBLE_REMOVAL":
                    sinfo["pending_removals"] += 1
                elif tstate == "POSSIBLE_PLACEMENT":
                    sinfo["pending_placements"] += 1

            if sinfo["is_empty"]:
                sinfo["status"] = "EMPTY"
            elif smoothed_val < (sinfo["capacity"] * 0.3):
                sinfo["status"] = "LOW_STOCK"
            else:
                sinfo["status"] = "NORMAL"

        return {
            "shelves": shelf_states,
            "misplaced_items": misplaced_items,
            "unassigned_items": unassigned_items
        }

shelf_monitor = ShelfMonitor()
