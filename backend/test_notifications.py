import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Set working directory and Python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
PARENT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from app.database import Base, SessionLocal, engine
from app import models
from app.notifications.email_service import EmailService
from app.notifications.email_templates import render_stock_alert_email, render_test_email
from app.inventory_logic import process_removal, process_addition

class TestNotificationSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.db = SessionLocal()
        # Seed test user
        self.test_user = self.db.query(models.User).filter(models.User.username == "test_admin").first()
        if not self.test_user:
            self.test_user = models.User(
                username="test_admin",
                full_name="Test Administrator",
                email="admin_test@smartshelf.org",
                hashed_password="dummy_hash_for_test",
                role="admin",
                is_active=True
            )
            self.db.add(self.test_user)
            self.db.commit()
            self.db.refresh(self.test_user)

        # Seed test product
        self.test_product = self.db.query(models.Product).filter(models.Product.name == "Test_Soda").first()
        if self.test_product:
            self.test_product.stock = 20
            self.test_product.threshold = 5
            self.test_product.notification_state = "NORMAL"
            self.db.commit()
        else:
            self.test_product = models.Product(
                name="Test_Soda",
                stock=20,
                threshold=5,
                price=2.5,
                category="Beverages",
                notification_state="NORMAL"
            )
            self.db.add(self.test_product)
            self.db.commit()
            self.db.refresh(self.test_product)

        self.db.query(models.NotificationLog).filter(models.NotificationLog.product_id == self.test_product.id).delete()
        self.db.commit()

        self.service = EmailService()

    def tearDown(self):
        try:
            self.service._executor.shutdown(wait=True)
        except Exception:
            pass
        self.db.close()

    def test_01_stock_above_threshold_no_email(self):
        """Test 1: Stock decrement above threshold does not send email."""
        self.test_product.stock = 15
        self.test_product.notification_state = "NORMAL"
        self.db.commit()

        alert = self.service.evaluate_and_notify(self.test_product, db_session=self.db)
        self.assertIsNone(alert)
        self.assertEqual(self.test_product.notification_state, "NORMAL")

    def test_02_transition_to_low_stock_triggers_email(self):
        """Test 2: Decrementing to threshold transitions to LOW_STOCK and triggers 1 alert."""
        self.test_product.stock = 5
        self.test_product.threshold = 5
        self.test_product.notification_state = "NORMAL"
        self.db.commit()

        # Mock the SMTP send to prevent actual internet transmission during test
        with patch.object(self.service, "_send_smtp", return_value=(True, None, 1)) as mock_send:
            alert = self.service.evaluate_and_notify(self.test_product, db_session=self.db)
            self.assertEqual(alert, "LOW_STOCK")
            self.assertEqual(self.test_product.notification_state, "LOW_STOCK")

            # Check notification log was inserted
            log = self.db.query(models.NotificationLog).filter(
                models.NotificationLog.product_id == self.test_product.id,
                models.NotificationLog.alert_type == "LOW_STOCK"
            ).order_by(models.NotificationLog.id.desc()).first()
            self.assertIsNotNone(log)
            self.assertIn("admin_test@smartshelf.org", log.recipient)

    def test_03_spam_prevention_on_continued_low_stock(self):
        """Test 3: Further decrements while already in LOW_STOCK do NOT send duplicate emails."""
        self.test_product.stock = 4  # Still low
        self.test_product.notification_state = "LOW_STOCK"
        self.db.commit()

        alert = self.service.evaluate_and_notify(self.test_product, db_session=self.db)
        self.assertIsNone(alert)  # No duplicate alert!
        self.assertEqual(self.test_product.notification_state, "LOW_STOCK")

    def test_04_transition_to_out_of_stock(self):
        """Test 4: Stock reaching 0 transitions to OUT_OF_STOCK and triggers critical alert."""
        self.test_product.stock = 0
        self.test_product.notification_state = "LOW_STOCK"
        self.db.commit()

        with patch.object(self.service, "_send_smtp", return_value=(True, None, 1)):
            alert = self.service.evaluate_and_notify(self.test_product, db_session=self.db)
            self.assertEqual(alert, "OUT_OF_STOCK")
            self.assertEqual(self.test_product.notification_state, "OUT_OF_STOCK")

            # Verify log entry
            log = self.db.query(models.NotificationLog).filter(
                models.NotificationLog.product_id == self.test_product.id,
                models.NotificationLog.alert_type == "OUT_OF_STOCK"
            ).order_by(models.NotificationLog.id.desc()).first()
            self.assertIsNotNone(log)

    def test_05_restock_resets_state_to_normal(self):
        """Test 5: Restocking above threshold resets state to NORMAL."""
        self.test_product.stock = 25
        self.test_product.notification_state = "OUT_OF_STOCK"
        self.db.commit()

        alert = self.service.evaluate_and_notify(self.test_product, db_session=self.db)
        self.assertEqual(alert, "RESET")
        self.assertEqual(self.test_product.notification_state, "NORMAL")

    def test_06_failure_resilience_never_rolls_back_inventory(self):
        """Test 6: If SMTP throws an exception, inventory remains successfully committed."""
        self.test_product.stock = 3
        self.test_product.notification_state = "NORMAL"
        self.db.commit()

        # Simulate catastrophic SMTP failure
        with patch.object(self.service, "_send_smtp", return_value=(False, "Connection refused", 3)):
            alert = self.service.evaluate_and_notify(self.test_product, db_session=self.db)
            # Notification returned alert type without crashing
            self.assertEqual(alert, "LOW_STOCK")

        # Verify product stock in DB is still 3!
        refreshed = self.db.query(models.Product).filter(models.Product.id == self.test_product.id).first()
        self.assertEqual(refreshed.stock, 3)

    def test_07_status_masks_credentials(self):
        """Test 7: get_status() never exposes GMAIL_APP_PASSWORD and masks sender."""
        status = self.service.get_status()
        self.assertIn("enabled", status)
        self.assertIn("configured", status)
        self.assertNotIn("password", str(status).lower())
        self.assertNotIn("app_password", str(status).lower())

    def test_08_test_email_queueing(self):
        """Test 8: send_test_email records pending log and queues background task."""
        with patch.object(self.service, "_send_smtp", return_value=(True, None, 1)):
            success, msg = self.service.send_test_email("admin_test@smartshelf.org", user_id=self.test_user.id)
            self.assertTrue(success)
            self.assertIn("queued", msg.lower())

            # Verify log entry created
            log = self.db.query(models.NotificationLog).filter(
                models.NotificationLog.alert_type == "TEST",
                models.NotificationLog.recipient == "admin_test@smartshelf.org"
            ).order_by(models.NotificationLog.id.desc()).first()
            self.assertIsNotNone(log)

    def test_09_email_templates_render_cleanly(self):
        """Test 9: Template renders without errors and includes necessary security escapes."""
        subj, html, txt = render_stock_alert_email(
            product_name="Sprite <script>alert('xss')</script>",
            current_stock=2,
            threshold=5,
            alert_type="LOW_STOCK"
        )
        self.assertIn("Sprite", subj)
        self.assertNotIn("<script>", html)  # XSS escaped!
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("SmartShelf Vision AI", html)

    def test_10_inventory_logic_integration(self):
        """Test 10: Calling process_removal updates inventory and triggers evaluate_and_notify."""
        self.test_product.stock = 6
        self.test_product.threshold = 5
        self.test_product.notification_state = "NORMAL"
        self.db.commit()

        with patch.object(self.service, "_send_smtp", return_value=(True, None, 1)):
            res = process_removal(self.test_product.name, quantity=2, confidence=0.98, db=self.db)
            self.assertEqual(res["stock"], 4)

            # Product stock in DB is 4, which is <= 5 threshold
            p = self.db.query(models.Product).filter(models.Product.name == self.test_product.name).first()
            self.assertEqual(p.stock, 4)
            self.assertEqual(p.notification_state, "LOW_STOCK")


if __name__ == "__main__":
    unittest.main()
