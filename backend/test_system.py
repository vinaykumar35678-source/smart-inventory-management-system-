"""
test_system.py — Comprehensive System Test Suite
Tests Computer Vision Pipeline, Multi-Object Tracking, Shelf Zones,
Pose Estimation, Temporal Behavior Engine, Anomaly Scoring, and REST APIs.
"""
import os
import sys
import unittest
import numpy as np
from datetime import datetime

# Set path to backend & root
BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, ROOT_DIR)

from app.database import SessionLocal, engine, Base
from app import models
from app.ai.detection.detector import detector
from app.ai.tracking.tracker import ByteTracker
from app.ai.pose.pose_estimator import pose_estimator
from app.ai.inventory.shelf_monitor import ShelfMonitor
from app.ai.behavior.behavior_analyzer import BehaviorAnalyzer
from app.ai.events.event_engine import event_engine
from app.ai.pipeline import pipeline

class TestSmartInventoryVisionSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        from app.auth import hash_password
        admin = cls.db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            admin = models.User(
                username="admin", full_name="Admin", role="admin", is_active=True,
                hashed_password=hash_password("Admin@123")
            )
            cls.db.add(admin)
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_yolo_detector(self):
        """Verify YOLO detector initialization, device selection, and inference."""
        self.assertIsNotNone(detector)
        self.assertIn(detector.device, ["cuda", "cpu"])
        
        # Test inference with synthetic blank 640x480 frame
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect(blank_frame)
        self.assertIsInstance(detections, list)
        print("✓ Test 1: YOLO Detector initialized and functional on device:", detector.device.upper())

    def test_02_bytetrack_multi_object_tracking(self):
        """Verify ByteTracker maintains unique tracking IDs across sequential frames."""
        tracker = ByteTracker(max_missing_frames=5, iou_threshold=0.3)
        
        # Frame 1 detections
        f1_dets = [
            {"label": "Person", "category": "person", "confidence": 0.92, "box": [100, 100, 200, 300]},
            {"label": "Milk (1L)", "category": "item", "confidence": 0.88, "box": [300, 150, 380, 260]}
        ]
        t1 = tracker.update(f1_dets)
        self.assertEqual(len(t1), 2)
        person_id = t1[0]["track_id"]
        product_id = t1[1]["track_id"]

        # Frame 2 detections (slightly moved)
        f2_dets = [
            {"label": "Person", "category": "person", "confidence": 0.94, "box": [105, 102, 205, 302]},
            {"label": "Milk (1L)", "category": "item", "confidence": 0.89, "box": [302, 151, 382, 261]}
        ]
        t2 = tracker.update(f2_dets)
        self.assertEqual(len(t2), 2)
        # Verify IDs are preserved!
        self.assertEqual(t2[0]["track_id"], person_id)
        self.assertEqual(t2[1]["track_id"], product_id)
        print(f"✓ Test 2: ByteTrack persistence verified (Person Track #{person_id}, Product Track #{product_id})")

    def test_03_shelf_roi_and_misplaced_detection(self):
        """Verify virtual shelf containment, counting, and category compatibility checks."""
        sm = ShelfMonitor()
        
        # Define mock shelf: Category 'Dairy' at [200, 100, 500, 400]
        class MockShelf:
            id = 1
            name = "Shelf 1 - Dairy"
            category = "Dairy"
            roi_x1 = 0.2
            roi_y1 = 0.2
            roi_x2 = 0.8
            roi_y2 = 0.8
            capacity = 10
            current_count = 0
            status = "NORMAL"

        sm.set_shelves_from_db([MockShelf()])
        frame_w, frame_h = 1000, 1000

        # Items: 1 valid Dairy item inside shelf, 1 Misplaced Fruit item inside Dairy shelf
        items = [
            {"track_id": 1, "label": "Milk (1L)", "category": "item", "centroid": (400, 300), "box": [350, 250, 450, 350], "confidence": 0.95},
            {"track_id": 2, "label": "Apple", "category": "item", "centroid": (450, 320), "box": [420, 290, 480, 350], "confidence": 0.91}
        ]

        eval_res = sm.evaluate(items, frame_w, frame_h)
        shelf_info = eval_res["shelves"][1]

        self.assertEqual(shelf_info["detected_count"], 2)
        self.assertEqual(len(eval_res["misplaced_items"]), 1)
        self.assertEqual(eval_res["misplaced_items"][0]["product"], "Apple")
        print("✓ Test 3: Shelf ROI containment & Misplaced Product detection verified.")

    def test_04_pose_estimation_and_reaching(self):
        """Verify pose estimation identifies reaching into shelf regions."""
        person_tracks = [
            {"track_id": 5, "box": [200, 200, 400, 600], "centroid": (300, 400), "confidence": 0.92}
        ]
        shelves = [
            {"id": 1, "name": "Shelf 1", "box": [250, 300, 500, 500]}
        ]
        blank_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        res = pose_estimator.estimate(blank_frame, person_tracks, shelves)
        self.assertEqual(len(res), 1)
        self.assertTrue(res[0]["is_reaching"])
        print("✓ Test 4: Pose and reaching estimation verified.")

    def test_05_behavior_and_temporal_state_machine(self):
        """Verify temporal confirmation of removal and multi-signal suspicious scoring."""
        ba = BehaviorAnalyzer()
        from app.ai.config.config import ai_config
        ai_config.update({
            "min_track_age": 1,
            "removal_confirmation_frames": 5,
            "min_movement_distance": 0.0,
            "removal_confirmation_time": 0.01
        })
        ba = BehaviorAnalyzer()
        shelf_eval = {
            "shelves": {1: {"id": 1, "name": "Electronics Shelf", "items": [{"track_id": 10}]}},
            "misplaced_items": []
        }
        tracked_item = [{
            "track_id": 10, "label": "Mobile Phone", "category": "item",
            "centroid": (150, 150), "box": [100, 100, 200, 200], "confidence": 0.95, "velocity": (25, 20)
        }]
        person = [{
            "track_id": 99, "label": "Person", "category": "person",
            "centroid": (160, 160), "box": [50, 50, 250, 400], "confidence": 0.95
        }]
        pose_results = [{"person_track_id": 99, "is_reaching": True}]

        # Frame 1: item on shelf
        ba.analyze_frame(tracked_item + person, shelf_eval, pose_results)

        # Subsequent frames: item leaves shelf ROI
        import time
        time.sleep(0.02)
        shelf_eval_empty = {"shelves": {1: {"items": []}}, "misplaced_items": []}
        events = []
        for _ in range(12):
            evs = ba.analyze_frame(tracked_item + person, shelf_eval_empty, pose_results)
            events.extend(evs)

        # Must generate verified removal and suspicious removal alert
        types = [e["event_type"] for e in events]
        self.assertIn("PRODUCT_REMOVED", types)
        self.assertIn("SUSPICIOUS_REMOVAL", types)
        print("✓ Test 5: Temporal removal confirmation & multi-signal suspicious score verified.")

    def test_06_event_engine_and_db_persistence(self):
        """Verify EventEngine updates stock, persists event, and creates alerts."""
        # Ensure product exists
        product = self.db.query(models.Product).filter(models.Product.name == "Apple").first()
        if not product:
            product = models.Product(name="Apple", stock=15, threshold=5, price=2.5, category="Fruits")
            self.db.add(product)
            self.db.commit()

        product.stock = max(10, product.stock)
        self.db.commit()
        initial_stock = product.stock
        ev = {
            "event_type": "PRODUCT_REMOVED",
            "product_name": "Apple",
            "tracking_id": 88,
            "shelf_id": 1,
            "quantity": 2,
            "confidence": 0.96,
            "status": "VERIFIED",
            "metadata": {"person_track_id": 12, "suspicious_score": 40}
        }
        res = event_engine.process_event(ev, self.db)
        self.assertEqual(res["product"], "Apple")

        # Verify stock was decremented
        self.db.refresh(product)
        self.assertEqual(product.stock, initial_stock - 2)
        print(f"✓ Test 6: Database stock decrement verified ({initial_stock} -> {product.stock}).")

    def test_07_fastapi_endpoints(self):
        """Verify REST API endpoints using FastAPI TestClient with auth."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import create_access_token

        client = TestClient(app)
        token, _, _ = create_access_token({"sub": "admin", "role": "admin"})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Status endpoint
        res = client.get("/api/detection/status", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("device", data)
        self.assertIn("model_name", data)

        # 2. Shelves endpoint
        res = client.get("/api/shelves", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

        # 3. Analytics endpoint
        res = client.get("/api/analytics", headers=headers)
        self.assertEqual(res.status_code, 200)
        an_data = res.json()
        self.assertIn("total_stock", an_data)
        self.assertIn("shelf_utilization", an_data)

        # 4. Demo Scenarios
        res = client.post("/api/demo/scenario/restock", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "SUCCESS")

        res = client.post("/api/demo/scenario/misplaced", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "SUCCESS")

        res = client.post("/api/demo/scenario/suspicious_removal", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "SUCCESS")

        print("✓ Test 7: FastAPI endpoints and College Viva Demo scenarios verified successfully.")

    def test_08_custom_dataset_and_model_management(self):
        """Verify Dataset Import, Validation, Preview, Model Registry, and Dynamic Hot-Swapping."""
        from ml.scripts.dataset_manager import dataset_manager
        from ml.scripts.model_manager import model_manager
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import create_access_token

        # 1. Test Dataset Validation on default 150-image dataset
        report = dataset_manager.validate_dataset("smart_shelf/dataset", "smart_shelf/data.yaml")
        self.assertTrue(report["is_valid"])
        self.assertEqual(report["summary"]["total_images"], 150)
        self.assertEqual(report["summary"]["total_labels"], 150)
        self.assertEqual(len(report["class_distribution"]), 13)

        # 2. Test Preview generation
        previews = dataset_manager.generate_previews("smart_shelf/dataset", max_samples=2)
        self.assertGreater(len(previews), 0)
        self.assertTrue(previews[0]["image_base64"].startswith("data:image/jpeg;base64,"))

        # 3. Test Model Manager listing & active model
        models_list = model_manager.list_models()
        self.assertGreaterEqual(len(models_list), 2)
        active_info = model_manager.get_active_model_info()
        self.assertIn("active_model_id", active_info)

        # 4. Test Model Comparison
        comp = model_manager.compare_models()
        self.assertIn("models_comparison", comp)
        self.assertGreaterEqual(len(comp["models_comparison"]), 2)

        # 5. Test Dynamic Detector Hot-Swapping
        switched = detector.switch_model("yolov8n.pt", {0: "Apple", 2: "Milk (1L)"})
        self.assertTrue(switched)
        self.assertEqual(detector.product_class_map.get(0), "Apple")

        # 6. Test ML REST API endpoints
        client = TestClient(app)
        token, _, _ = create_access_token({"sub": "admin", "role": "admin"})
        headers = {"Authorization": f"Bearer {token}"}

        # Datasets list
        r1 = client.get("/api/ml/datasets", headers=headers)
        self.assertEqual(r1.status_code, 200)
        self.assertIsInstance(r1.json(), list)

        # Dataset validation API
        r2 = client.post("/api/ml/datasets/validate", json={
            "dataset_path": "smart_shelf/dataset",
            "yaml_path": "smart_shelf/data.yaml"
        }, headers=headers)
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json()["is_valid"])

        # Models list API
        r3 = client.get("/api/ml/models", headers=headers)
        self.assertEqual(r3.status_code, 200)

        # Compare API
        r4 = client.get("/api/ml/models/compare", headers=headers)
        self.assertEqual(r4.status_code, 200)

        print("✓ Test 8: Custom Dataset Validation, BBox Previews, Model Management & Hot-Swapping verified.")

if __name__ == "__main__":
    unittest.main()
