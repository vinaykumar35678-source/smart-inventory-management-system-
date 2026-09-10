"""
behavior_analyzer.py — Formalized Product Temporal State Machine & Loss Prevention Engine
Implements strict state lifecycle transitions:
  NEW -> STABLE_ON_SHELF -> INTERACTING -> POSSIBLE_REMOVAL -> REMOVAL_CONFIRMED
  OUTSIDE_SHELF -> POSSIBLE_PLACEMENT -> PLACEMENT_CONFIRMED
  TEMPORARILY_OCCLUDED (held during grace period, no inventory decrement)
Eliminates simultaneous add/remove flickering via event cooldowns and state validation.
"""
import time
import uuid
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from ..config.config import ai_config
from ..tracking.tracker import TrackState

class BehaviorAnalyzer:
    """
    State Machine & Temporal Behavior Engine.
    Enforces multi-frame confirmation before emitting validated inventory events.
    """
    def __init__(self):
        # Product state tracker: {track_id: dict}
        self.product_states: Dict[int, Dict[str, Any]] = {}
        
        # Stability frame counters: {track_id: int}
        self.outside_frame_counts: Dict[int, int] = defaultdict(int)
        self.inside_frame_counts: Dict[int, int] = defaultdict(int)

        # Event debounce & cooldown: {track_id: {"last_event": str, "timestamp": float}}
        self.track_event_history: Dict[int, Dict[str, Any]] = {}

        # Set of active pending removals: {track_id: start_timestamp}
        self.pending_removals: Dict[int, float] = {}
        self.pending_placements: Dict[int, float] = {}

    def analyze_frame(
        self,
        tracked_objects: List[Dict[str, Any]],
        shelf_eval: Dict[str, Any],
        pose_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Processes tracked objects across the state machine and returns validated events.
        """
        generated_events = []
        now = time.time()

        min_track_age = int(ai_config.get("min_track_age", 10))
        removal_frames_thresh = int(ai_config.get("removal_confirmation_frames", 15))
        placement_frames_thresh = int(ai_config.get("placement_confirmation_frames", 15))
        removal_time_thresh = float(ai_config.get("removal_confirmation_time", 1.0))
        cooldown_sec = float(ai_config.get("event_cooldown_seconds", 2.0))
        suspicious_score_thresh = int(ai_config.get("suspicious_score_threshold", 70))
        min_move_dist = float(ai_config.get("min_movement_distance", 30.0))

        # Separate persons and validated inventory items
        persons = [o for o in tracked_objects if o.get("category") == "person"]
        items = [o for o in tracked_objects if o.get("category") == "item"]

        # Map shelf contents by track_id
        items_inside_shelves = {}
        for s_id, s_info in shelf_eval["shelves"].items():
            for item in s_info["items"]:
                items_inside_shelves[item["track_id"]] = s_id

        # Evaluate each product track
        for item in items:
            tid = item["track_id"]
            label = item["label"]
            conf = item["confidence"]
            cx, cy = item["centroid"]
            current_shelf_id = items_inside_shelves.get(tid)
            is_occluded = item.get("is_occluded", False)

            # ── 1. Initialize Track in State Machine ───────────────
            if tid not in self.product_states:
                initial_state = TrackState.STABLE_ON_SHELF if current_shelf_id is not None else TrackState.NEW
                self.product_states[tid] = {
                    "track_id": tid,
                    "label": label,
                    "state": initial_state,
                    "initial_shelf": current_shelf_id,
                    "last_seen_shelf": current_shelf_id,
                    "first_seen": now,
                    "state_enter_time": now,
                    "interacted_by_person": None,
                    "baseline_pos": (cx, cy),
                    "suspicious_score": 0,
                    "last_confirmed_event": None,
                    "last_event_time": 0.0
                }

            p_state = self.product_states[tid]

            # ── 2. Handle Temporary Occlusion ─────────────────────
            # If the product is occluded, maintain current state — NEVER trigger removal!
            if is_occluded:
                item["track_state"] = TrackState.TEMPORARILY_OCCLUDED
                continue

            # ── 3. Proximity to Persons & Hands ────────────────────
            nearest_person_id = None
            min_dist_to_person = 9999.0
            for p in persons:
                px, py = p["centroid"]
                dist = np.sqrt((cx - px)**2 + (cy - py)**2)
                if dist < min_dist_to_person:
                    min_dist_to_person = dist
                    if dist < 160:
                        nearest_person_id = p["track_id"]

            if nearest_person_id:
                p_state["interacted_by_person"] = nearest_person_id

            # Movement from baseline
            bx, by = p_state["baseline_pos"]
            movement_dist = np.sqrt((cx - bx)**2 + (cy - by)**2)

            # ── 4. State Transitions ──────────────────────────────
            curr_state = p_state["state"]

            # Transition: NEW -> STABLE_ON_SHELF or OUTSIDE_SHELF
            if curr_state == TrackState.NEW:
                if current_shelf_id is not None:
                    self.inside_frame_counts[tid] += 1
                    if self.inside_frame_counts[tid] >= min_track_age:
                        p_state["state"] = TrackState.STABLE_ON_SHELF
                        p_state["initial_shelf"] = current_shelf_id
                        p_state["last_seen_shelf"] = current_shelf_id
                        p_state["state_enter_time"] = now
                else:
                    self.outside_frame_counts[tid] += 1
                    if self.outside_frame_counts[tid] >= min_track_age:
                        p_state["state"] = "OUTSIDE_SHELF"
                        p_state["state_enter_time"] = now

                item["track_state"] = p_state["state"]
                continue

            # Transition: STABLE_ON_SHELF -> INTERACTING
            if curr_state == TrackState.STABLE_ON_SHELF:
                p_state["last_seen_shelf"] = current_shelf_id or p_state["last_seen_shelf"]
                if nearest_person_id is not None or movement_dist > 15:
                    p_state["state"] = TrackState.INTERACTING
                    p_state["state_enter_time"] = now

            # Transition: (STABLE_ON_SHELF / INTERACTING) -> POSSIBLE_REMOVAL
            if curr_state in (TrackState.STABLE_ON_SHELF, TrackState.INTERACTING):
                # If product exits the shelf ROI
                if current_shelf_id is None:
                    self.outside_frame_counts[tid] += 1
                    self.inside_frame_counts[tid] = 0
                    p_state["state"] = TrackState.POSSIBLE_REMOVAL
                    p_state["state_enter_time"] = now
                    self.pending_removals[tid] = now
                else:
                    self.inside_frame_counts[tid] += 1
                    self.outside_frame_counts[tid] = 0

            # Evaluation while in POSSIBLE_REMOVAL
            elif curr_state == TrackState.POSSIBLE_REMOVAL:
                # If item returned to shelf before confirmation: cancel removal!
                if current_shelf_id is not None:
                    self.outside_frame_counts[tid] = 0
                    self.inside_frame_counts[tid] += 1
                    p_state["state"] = TrackState.STABLE_ON_SHELF
                    self.pending_removals.pop(tid, None)
                else:
                    self.outside_frame_counts[tid] += 1
                    elapsed_outside = now - p_state["state_enter_time"]

                    # Check multi-frame & time confirmation thresholds
                    if (self.outside_frame_counts[tid] >= removal_frames_thresh and 
                        (elapsed_outside >= removal_time_thresh or self.outside_frame_counts[tid] >= removal_frames_thresh + 3) and
                        movement_dist >= min_move_dist):
                        
                        # Check cooldown against simultaneous events
                        last_ev = p_state["last_confirmed_event"]
                        last_ev_time = p_state["last_event_time"]

                        if last_ev != "PRODUCT_REMOVED" or (now - last_ev_time) > cooldown_sec:
                            p_state["state"] = TrackState.REMOVAL_CONFIRMED
                            p_state["last_confirmed_event"] = "PRODUCT_REMOVED"
                            p_state["last_event_time"] = now
                            self.pending_removals.pop(tid, None)

                            # Calculate Suspicious Loss Prevention Score
                            score = 35 # Base verified removal score
                            if nearest_person_id is not None:
                                score += 20
                            has_hand_reaching = any(
                                pr.get("is_reaching") for pr in pose_results 
                                if pr.get("person_track_id") == nearest_person_id
                            )
                            if has_hand_reaching:
                                score += 25
                            vx, vy = item.get("velocity", (0, 0))
                            if np.sqrt(vx**2 + vy**2) > 15:
                                score += 20
                            p_state["suspicious_score"] = min(100, score)

                            # Generate verified PRODUCT_REMOVED event
                            event_id = str(uuid.uuid4())
                            ev_payload = {
                                "event_id": event_id,
                                "event_type": "PRODUCT_REMOVED",
                                "product_name": label,
                                "tracking_id": tid,
                                "shelf_id": p_state.get("last_seen_shelf") or 1,
                                "quantity": 1,
                                "confidence": conf,
                                "status": "VERIFIED",
                                "metadata": {
                                    "person_track_id": nearest_person_id,
                                    "suspicious_score": score,
                                    "outside_frames": self.outside_frame_counts[tid],
                                    "duration_outside": round(elapsed_outside, 2)
                                }
                            }
                            generated_events.append(ev_payload)

                            # If suspicious threshold exceeded, emit alert event
                            if score >= suspicious_score_thresh:
                                generated_events.append({
                                    "event_id": str(uuid.uuid4()),
                                    "event_type": "SUSPICIOUS_REMOVAL",
                                    "product_name": label,
                                    "tracking_id": tid,
                                    "shelf_id": p_state.get("last_seen_shelf") or 1,
                                    "quantity": 1,
                                    "confidence": conf,
                                    "status": "SUSPICIOUS",
                                    "metadata": {
                                        "person_track_id": nearest_person_id,
                                        "suspicious_score": score,
                                        "reason": "Unverified product removal outside shelf zone"
                                    }
                                })

            # ── SCENARIO: Placement Detection ─────────────────────
            # Transition: (OUTSIDE_SHELF / REMOVAL_CONFIRMED) -> POSSIBLE_PLACEMENT
            if curr_state in (TrackState.REMOVAL_CONFIRMED, "OUTSIDE_SHELF") and current_shelf_id is not None:
                self.inside_frame_counts[tid] += 1
                p_state["state"] = TrackState.POSSIBLE_PLACEMENT
                p_state["state_enter_time"] = now
                self.pending_placements[tid] = now

            elif curr_state == TrackState.POSSIBLE_PLACEMENT:
                if current_shelf_id is None:
                    # Left shelf again before confirmation
                    self.inside_frame_counts[tid] = 0
                    p_state["state"] = "OUTSIDE_SHELF"
                    self.pending_placements.pop(tid, None)
                else:
                    self.inside_frame_counts[tid] += 1
                    elapsed_inside = now - p_state["state_enter_time"]

                    placement_time_thresh = float(ai_config.get("removal_confirmation_time", 0.05))
                    if (self.inside_frame_counts[tid] >= placement_frames_thresh and 
                        elapsed_inside >= placement_time_thresh):
                        
                        last_ev = p_state["last_confirmed_event"]
                        last_ev_time = p_state["last_event_time"]

                        # Prevent simultaneous add/remove: must satisfy cooldown
                        if last_ev != "PRODUCT_PLACED" or (now - last_ev_time) > cooldown_sec:
                            p_state["state"] = TrackState.STABLE_ON_SHELF
                            p_state["last_confirmed_event"] = "PRODUCT_PLACED"
                            p_state["last_event_time"] = now
                            p_state["last_seen_shelf"] = current_shelf_id
                            self.pending_placements.pop(tid, None)

                            generated_events.append({
                                "event_id": str(uuid.uuid4()),
                                "event_type": "PRODUCT_PLACED",
                                "product_name": label,
                                "tracking_id": tid,
                                "shelf_id": current_shelf_id,
                                "quantity": 1,
                                "confidence": conf,
                                "status": "VERIFIED",
                                "metadata": {
                                    "inside_frames": self.inside_frame_counts[tid],
                                    "shelf_name": shelf_eval["shelves"].get(current_shelf_id, {}).get("name")
                                }
                            })

            # Update item dictionary with current state machine values
            item["track_state"] = p_state["state"]

        # ── 5. Evaluate Tracks That Have Disappeared Permanently ────
        active_tids = {item["track_id"] for item in items}
        for tid, p_state in list(self.product_states.items()):
            if tid not in active_tids:
                if p_state["state"] in (TrackState.STABLE_ON_SHELF, TrackState.INTERACTING, TrackState.POSSIBLE_REMOVAL):
                    if p_state.get("last_confirmed_event") != "PRODUCT_REMOVED":
                        p_state["state"] = TrackState.REMOVAL_CONFIRMED
                        p_state["last_confirmed_event"] = "PRODUCT_REMOVED"
                        p_state["last_event_time"] = now
                        self.pending_removals.pop(tid, None)

                        generated_events.append({
                            "event_id": str(uuid.uuid4()),
                            "event_type": "PRODUCT_REMOVED",
                            "product_name": p_state["label"],
                            "tracking_id": tid,
                            "shelf_id": p_state.get("last_seen_shelf") or 1,
                            "quantity": 1,
                            "confidence": 0.9,
                            "status": "VERIFIED",
                            "metadata": {
                                "reason": "Permanent disappearance from shelf zone after grace period"
                            }
                        })

        return generated_events

    def get_pending_summary(self) -> Dict[str, Any]:
        """Return counts of currently pending state transitions."""
        return {
            "pending_removals_count": len(self.pending_removals),
            "pending_placements_count": len(self.pending_placements)
        }

    def reset(self):
        """Reset state machine."""
        self.product_states.clear()
        self.outside_frame_counts.clear()
        self.inside_frame_counts.clear()
        self.track_event_history.clear()
        self.pending_removals.clear()
        self.pending_placements.clear()

behavior_analyzer = BehaviorAnalyzer()
