"""
test_counting_logic.py — Comprehensive 12-Scenario Automated Test Suite
Tests all 12 validation scenarios specified by the user:
  TEST 1: Product remains stationary -> No inventory changes.
  TEST 2: Product temporarily hidden -> No inventory changes.
  TEST 3: Product detection disappears for 2-3 frames -> No inventory changes.
  TEST 4: Product is genuinely removed from shelf -> Exactly -1.
  TEST 5: Product is placed on shelf -> Exactly +1.
  TEST 6: Product is removed and placed back -> Exactly -1, followed later by +1.
  TEST 7: Product remains visible but confidence fluctuates -> No false removal.
  TEST 8: Two identical products next to each other -> Separate persistent track IDs.
  TEST 9: One product is moved while another remains stationary -> Only moved product generates an event.
  TEST 10: Person blocks multiple products -> No false inventory reduction.
  TEST 11: Product is temporarily lost and tracker recovers it -> Same inventory count & track ID restored.
  TEST 12: A product disappears permanently -> One and ONLY one removal event.
"""
import os
import sys
import unittest
import time
from unittest.mock import MagicMock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if os.path.join(ROOT_DIR, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

from app.ai.tracking.tracker import ByteTracker, TrackState
from app.ai.inventory.shelf_monitor import ShelfMonitor
from app.ai.behavior.behavior_analyzer import BehaviorAnalyzer
from app.ai.events.event_engine import EventEngine
from app.ai.config.config import ai_config

class TestCountingLogic12Scenarios(unittest.TestCase):

    def setUp(self):
        # Configure fast testing thresholds
        ai_config.update({
            "removal_confirmation_frames": 5,
            "placement_confirmation_frames": 5,
            "min_track_age": 3,
            "lost_grace_frames": 6,
            "shelf_exit_margin": 10,
            "min_movement_distance": 20.0,
            "event_cooldown_seconds": 0.4,
            "removal_confirmation_time": 0.04
        })

        self.tracker = ByteTracker()
        self.shelf_monitor = ShelfMonitor()
        self.behavior = BehaviorAnalyzer()
        self.event_engine = EventEngine()

        # Mock Shelf 1: [100, 100, 300, 300] on a 640x480 frame
        mock_shelf = MagicMock()
        mock_shelf.id = 1
        mock_shelf.name = "Produce Shelf"
        mock_shelf.category = "Fruits"
        mock_shelf.roi_x1 = 100 / 640
        mock_shelf.roi_y1 = 100 / 480
        mock_shelf.roi_x2 = 300 / 640
        mock_shelf.roi_y2 = 300 / 480
        mock_shelf.capacity = 10
        mock_shelf.current_count = 5
        mock_shelf.status = "NORMAL"

        self.shelf_monitor.set_shelves_from_db([mock_shelf])

    def run_frame(self, detections, persons=None):
        """Simulate single pipeline step without real camera."""
        all_dets = list(detections)
        if persons:
            all_dets.extend(persons)

        tracked = self.tracker.update(all_dets)
        shelf_eval = self.shelf_monitor.evaluate(tracked, 640, 480)
        events = self.behavior.analyze_frame(tracked, shelf_eval, [])
        return tracked, shelf_eval, events

    def simulate_motion(self, label, class_id, start_box, end_box, steps=6, other_items=None):
        """Simulates smooth frame-by-frame physical movement preserving IoU overlap."""
        all_events = []
        for s in range(1, steps + 1):
            alpha = s / steps
            box = [
                int(start_box[0] + alpha * (end_box[0] - start_box[0])),
                int(start_box[1] + alpha * (end_box[1] - start_box[1])),
                int(start_box[2] + alpha * (end_box[2] - start_box[2])),
                int(start_box[3] + alpha * (end_box[3] - start_box[3]))
            ]
            dets = [{"label": label, "category": "item", "class_id": class_id, "confidence": 0.90, "box": box}]
            if other_items:
                dets.extend(other_items)
            _, _, evs = self.run_frame(dets)
            all_events.extend(evs)
            time.sleep(0.01)
        return all_events

    # ── TEST 1: Product remains stationary ────────────────────────────────────
    def test_01_product_stationary(self):
        """Product remains stationary -> No inventory changes."""
        stationary_det = [{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.92, "box": [180, 180, 220, 220]}]
        
        all_events = []
        for _ in range(25):
            _, _, events = self.run_frame(stationary_det)
            all_events.extend(events)

        self.assertEqual(len(all_events), 0, "Stationary product should produce 0 inventory events")
        print("✓ Test 1 Passed: Product remains stationary -> 0 inventory changes.")

    # ── TEST 2: Product temporarily hidden (occluded) ─────────────────────────
    def test_02_product_temporarily_hidden(self):
        """Product temporarily hidden -> No inventory changes."""
        det = [{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.92, "box": [180, 180, 220, 220]}]
        
        # Frame 1-5: Visible
        for _ in range(5):
            self.run_frame(det)

        # Frame 6-8: Hidden (3 frames < lost_grace_frames of 6)
        for _ in range(3):
            tracked, shelf_eval, events = self.run_frame([])
            self.assertEqual(len(events), 0, "Hidden frames within grace period must NOT trigger removal")

        # Frame 9-14: Reappears
        all_events = []
        for _ in range(5):
            _, _, events = self.run_frame(det)
            all_events.extend(events)

        self.assertEqual(len(all_events), 0, "Occluded product should not produce removal events")
        print("✓ Test 2 Passed: Product temporarily hidden -> 0 inventory changes.")

    # ── TEST 3: Product detection disappears for 2-3 frames ───────────────────
    def test_03_detection_disappears_few_frames(self):
        """Product detection drops for 2-3 frames -> No inventory changes."""
        det = [{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.92, "box": [180, 180, 220, 220]}]
        
        # Establish track
        for _ in range(5):
            self.run_frame(det)

        # Drop 3 frames
        for _ in range(3):
            tracked, shelf_eval, events = self.run_frame([])
            self.assertEqual(len(events), 0, "2-3 frame drop must NEVER generate removal")

        # Re-detect
        for _ in range(5):
            _, _, events = self.run_frame(det)
            self.assertEqual(len(events), 0)

        print("✓ Test 3 Passed: Detection drops 2-3 frames -> 0 inventory changes.")

    # ── TEST 4: Product is genuinely removed from shelf ───────────────────────
    def test_04_genuine_removal(self):
        """Product moved smoothly outside shelf for >= confirmation frames -> Exactly 1 removal event."""
        start_box = [180, 180, 220, 220]  # Center (200, 200) inside shelf
        end_box = [340, 260, 380, 300]    # Center (360, 280) outside shelf (x > 300+margin)

        # 1. Establish stable baseline on shelf
        for _ in range(5):
            self.run_frame([{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": start_box}])

        # 2. Move smoothly outside shelf
        motion_events = self.simulate_motion("Apple", 0, start_box, end_box, steps=6)

        # 3. Hold outside shelf to satisfy confirmation frames
        outside_det = [{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.88, "box": end_box}]
        time.sleep(0.05)
        for _ in range(7):
            _, _, evs = self.run_frame(outside_det)
            motion_events.extend(evs)

        removal_events = [e for e in motion_events if e.get("event_type") == "PRODUCT_REMOVED"]
        self.assertEqual(len(removal_events), 1, f"Expected exactly 1 removal event, got {len(removal_events)}")
        self.assertEqual(removal_events[0]["quantity"], 1)
        print("✓ Test 4 Passed: Genuine removal -> Exactly -1 removal event.")

    # ── TEST 5: Product is placed on shelf ───────────────────────────────────
    def test_05_product_placed_on_shelf(self):
        """Product moved from outside into shelf ROI -> Exactly 1 placement event."""
        outside_box = [350, 280, 390, 320]  # Outside shelf
        inside_box = [180, 180, 220, 220]   # Inside shelf

        # 1. Product detected outside shelf
        for _ in range(5):
            self.run_frame([{"label": "Banana", "category": "item", "class_id": 1, "confidence": 0.91, "box": outside_box}])

        # 2. Move smoothly into shelf
        motion_events = self.simulate_motion("Banana", 1, outside_box, inside_box, steps=6)

        # 3. Hold inside shelf to satisfy confirmation frames
        inside_det = [{"label": "Banana", "category": "item", "class_id": 1, "confidence": 0.91, "box": inside_box}]
        time.sleep(0.05)
        for _ in range(7):
            _, _, evs = self.run_frame(inside_det)
            motion_events.extend(evs)

        placement_events = [e for e in motion_events if e.get("event_type") == "PRODUCT_PLACED"]
        self.assertEqual(len(placement_events), 1, f"Expected exactly 1 placement event, got {len(placement_events)}")
        self.assertEqual(placement_events[0]["quantity"], 1)
        print("✓ Test 5 Passed: Product placed on shelf -> Exactly +1 placement event.")

    # ── TEST 6: Product is removed and placed back ────────────────────────────
    def test_06_removed_and_placed_back(self):
        """Product removed then placed back -> Exactly -1 followed by +1 (no simultaneous conflict)."""
        inside_box = [180, 180, 220, 220]
        outside_box = [350, 280, 390, 320]

        # 1. Establish on shelf
        for _ in range(5):
            self.run_frame([{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": inside_box}])

        # 2. Remove smoothly
        evs1 = self.simulate_motion("Apple", 0, inside_box, outside_box, steps=6)
        time.sleep(0.05)
        for _ in range(7):
            _, _, e = self.run_frame([{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": outside_box}])
            evs1.extend(e)

        removals = [e for e in evs1 if e.get("event_type") == "PRODUCT_REMOVED"]
        self.assertEqual(len(removals), 1)

        # Wait for event cooldown
        time.sleep(0.45)

        # 3. Place back smoothly
        evs2 = self.simulate_motion("Apple", 0, outside_box, inside_box, steps=6)
        time.sleep(0.05)
        for _ in range(7):
            _, _, e = self.run_frame([{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": inside_box}])
            evs2.extend(e)

        placements = [e for e in evs2 if e.get("event_type") == "PRODUCT_PLACED"]
        self.assertEqual(len(placements), 1)
        print("✓ Test 6 Passed: Removed and placed back -> Exactly -1 followed by +1.")

    # ── TEST 7: Product confidence fluctuates ─────────────────────────────────
    def test_07_confidence_fluctuation(self):
        """Product confidence fluctuates between 0.90 and 0.46 -> No false removal."""
        confs = [0.91, 0.48, 0.85, 0.46, 0.94, 0.50, 0.88]
        events_accum = []
        for c in confs:
            det = [{"label": "Apple", "category": "item", "class_id": 0, "confidence": c, "box": [180, 180, 220, 220]}]
            _, _, evs = self.run_frame(det)
            events_accum.extend(evs)

        self.assertEqual(len(events_accum), 0, "Confidence fluctuations inside shelf must NOT trigger removals")
        print("✓ Test 7 Passed: Confidence fluctuates -> No false removal.")

    # ── TEST 8: Two identical products adjacent ───────────────────────────────
    def test_08_two_identical_products(self):
        """Two identical products next to each other receive separate persistent track IDs."""
        two_apples = [
            {"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": [150, 180, 190, 220]},
            {"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.92, "box": [210, 180, 250, 220]}
        ]

        last_tracked = []
        for _ in range(5):
            last_tracked, _, _ = self.run_frame(two_apples)

        self.assertEqual(len(last_tracked), 2)
        tids = [t["track_id"] for t in last_tracked]
        self.assertEqual(len(set(tids)), 2, "Each product must have a unique, persistent track ID")
        print("✓ Test 8 Passed: Two identical products adjacent -> Separate persistent track IDs.")

    # ── TEST 9: One product moved while another remains stationary ────────────
    def test_09_one_moved_one_stationary(self):
        """Only the moved product generates a removal event; stationary product generates 0."""
        p1_box = [150, 180, 190, 220]
        p2_start = [210, 180, 250, 220]
        p2_end = [340, 260, 380, 300]

        # Establish both on shelf
        for _ in range(5):
            self.run_frame([
                {"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": p1_box},
                {"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": p2_start}
            ])

        # Move p2 smoothly outside while p1 stays still
        other = [{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": p1_box}]
        evs = self.simulate_motion("Apple", 0, p2_start, p2_end, steps=6, other_items=other)
        
        time.sleep(0.05)
        for _ in range(7):
            _, _, e = self.run_frame([
                {"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": p1_box},
                {"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": p2_end}
            ])
            evs.extend(e)

        removal_events = [e for e in evs if e.get("event_type") == "PRODUCT_REMOVED"]
        self.assertEqual(len(removal_events), 1, "Only the moved product should generate a removal event")
        print("✓ Test 9 Passed: One moved, one stationary -> Only moved product decrements.")

    # ── TEST 10: Person blocks multiple products ──────────────────────────────
    def test_10_person_blocks_products(self):
        """Person temporarily blocks multiple products -> No false inventory reduction."""
        products = [
            {"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": [150, 180, 190, 220]},
            {"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": [210, 180, 250, 220]}
        ]

        # 1. Products visible
        for _ in range(5):
            self.run_frame(products)

        # 2. Person walks in front (products occluded for 3 frames)
        person = [{"label": "Person", "category": "person", "class_id": 99, "confidence": 0.95, "box": [140, 100, 270, 320]}]
        for _ in range(3):
            tracked, shelf_eval, evs = self.run_frame([], persons=person)
            self.assertEqual(len(evs), 0, "Person occluding products must NOT trigger removal")

        # 3. Person leaves, products visible again
        for _ in range(5):
            _, _, evs = self.run_frame(products)
            self.assertEqual(len(evs), 0)

        print("✓ Test 10 Passed: Person blocks multiple products -> No false reductions.")

    # ── TEST 11: Product temporarily lost and recovered ───────────────────────
    def test_11_track_recovery(self):
        """Product disappears for 3 frames, tracker recovers original track ID upon return."""
        det = [{"label": "Milk", "category": "item", "class_id": 2, "confidence": 0.92, "box": [180, 180, 220, 220]}]
        
        # Get original track ID
        tracked, _, _ = self.run_frame(det)
        orig_id = tracked[0]["track_id"]

        # Drop 3 frames
        for _ in range(3):
            self.run_frame([])

        # Reappears
        recovered_tracked, _, evs = self.run_frame(det)
        self.assertEqual(len(evs), 0)
        self.assertEqual(recovered_tracked[0]["track_id"], orig_id, "Tracker must preserve the original track ID")
        print("✓ Test 11 Passed: Product lost and recovered -> Original track ID preserved.")

    # ── TEST 12: Product disappears permanently ───────────────────────────────
    def test_12_disappears_permanently(self):
        """Product on shelf disappears permanently (> lost_grace_frames) -> Exactly ONE removal event."""
        on_shelf = [{"label": "Apple", "category": "item", "class_id": 0, "confidence": 0.90, "box": [180, 180, 220, 220]}]

        # Establish on shelf
        for _ in range(5):
            self.run_frame(on_shelf)

        # Disappears completely for 12 frames (> lost_grace_frames of 6)
        total_removals = 0
        for _ in range(12):
            _, _, evs = self.run_frame([])
            total_removals += sum(1 for e in evs if e.get("event_type") == "PRODUCT_REMOVED")

        self.assertEqual(total_removals, 1, f"Expected exactly 1 removal event for permanently lost product, got {total_removals}")

        # Keep running empty frames: MUST NOT trigger second removal event!
        for _ in range(10):
            _, _, evs = self.run_frame([])
            total_removals += sum(1 for e in evs if e.get("event_type") == "PRODUCT_REMOVED")

        self.assertEqual(total_removals, 1, "Permanent disappearance must NEVER trigger duplicate removals")
        print("✓ Test 12 Passed: Permanent disappearance -> Exactly one and ONLY one removal event.")

if __name__ == "__main__":
    unittest.main()
