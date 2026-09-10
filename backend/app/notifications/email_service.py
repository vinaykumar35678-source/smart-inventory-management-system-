import logging
import smtplib
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple

try:
    from app.config import settings
    from app.database import SessionLocal
    from app.models import NotificationLog, Product, User, Shelf
    from app.notifications.email_templates import (
        render_stock_alert_email,
        render_test_email,
    )
except ImportError:
    from ..config import settings
    from ..database import SessionLocal
    from ..models import NotificationLog, Product, User, Shelf
    from .email_templates import (
        render_stock_alert_email,
        render_test_email,
    )

logger = logging.getLogger("smartshelf.notifications")

class EmailService:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email_worker")

    def is_configured(self) -> bool:
        """Returns True if SMTP credentials and settings are present."""
        return bool(
            settings.GMAIL_ENABLED
            and settings.GMAIL_USERNAME
            and settings.GMAIL_APP_PASSWORD
            and settings.SMTP_HOST
        )

    def get_status(self) -> dict:
        """Safe status representation with no passwords exposed."""
        configured = self.is_configured()
        # Mask sender email for display
        sender = settings.GMAIL_FROM or settings.GMAIL_USERNAME or ""
        masked_sender = sender
        if "@" in sender:
            parts = sender.split("@")
            if len(parts[0]) > 3:
                masked_sender = f"{parts[0][:3]}***@{parts[1]}"
            else:
                masked_sender = f"***@{parts[1]}"

        return {
            "enabled": settings.GMAIL_ENABLED,
            "configured": configured,
            "smtp_host": settings.SMTP_HOST,
            "smtp_port": settings.SMTP_PORT,
            "sender_masked": masked_sender,
            "use_tls": settings.SMTP_USE_TLS,
        }

    def _send_smtp(
        self,
        recipient: str,
        subject: str,
        html_content: str,
        text_content: str,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[str], int]:
        """
        Synchronous SMTP sender with retry logic and exponential backoff.
        Returns: (success: bool, error_message: Optional[str], attempts_made: int)
        """
        if not self.is_configured():
            msg = "SMTP not configured: GMAIL_USERNAME or GMAIL_APP_PASSWORD missing"
            logger.warning(msg)
            return False, msg, 0

        sender = settings.GMAIL_FROM or settings.GMAIL_USERNAME
        sender_display = f"{settings.GMAIL_FROM_NAME} <{sender}>"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_display
        msg["To"] = recipient
        msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        attempts = 0
        last_err = None

        for attempt in range(1, max_retries + 1):
            attempts = attempt
            server = None
            try:
                if settings.SMTP_PORT == 465:
                    server = smtplib.SMTP_SSL(
                        settings.SMTP_HOST,
                        settings.SMTP_PORT,
                        timeout=settings.SMTP_TIMEOUT
                    )
                else:
                    server = smtplib.SMTP(
                        settings.SMTP_HOST,
                        settings.SMTP_PORT,
                        timeout=settings.SMTP_TIMEOUT
                    )
                    if settings.SMTP_USE_TLS:
                        server.starttls()

                server.login(settings.GMAIL_USERNAME, settings.GMAIL_APP_PASSWORD)
                server.sendmail(sender, [recipient], msg.as_string())
                logger.info(f"Email successfully delivered to {recipient} (attempt {attempt})")
                return True, None, attempts
            except Exception as e:
                # Sanitize error to ensure app password is never leaked in log
                err_str = str(e).replace(settings.GMAIL_APP_PASSWORD, "********")
                last_err = err_str
                logger.warning(f"SMTP send attempt {attempt}/{max_retries} failed to {recipient}: {err_str}")
                if attempt < max_retries:
                    time.sleep(attempt * 1.5)  # Exponential backoff
            finally:
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass

        return False, last_err or "Unknown SMTP error", attempts

    def _dispatch_email_job(
        self,
        log_id: int,
        recipient: str,
        subject: str,
        html_content: str,
        text_content: str
    ):
        """Worker thread entrypoint for asynchronous dispatch and log updating."""
        db = SessionLocal()
        try:
            success, error_msg, retries = self._send_smtp(
                recipient=recipient,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                max_retries=3
            )

            db.query(NotificationLog).filter(NotificationLog.id == log_id).update({
                NotificationLog.status: "SENT" if success else "FAILED",
                NotificationLog.sent_at: datetime.utcnow() if success else None,
                NotificationLog.error_message: error_msg,
                NotificationLog.retry_count: retries,
            })
            db.commit()
        except Exception as e:
            logger.error(f"Error updating NotificationLog {log_id}: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    def send_test_email(self, recipient: str, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Sends a test email to verify credentials.
        Returns: (enqueued: bool, message: str)
        """
        if not recipient or "@" not in recipient:
            return False, "Invalid recipient email address"

        subject, html_content, text_content = render_test_email(recipient)

        db = SessionLocal()
        try:
            log_entry = NotificationLog(
                notification_id=str(uuid.uuid4()),
                user_id=user_id,
                product_id=None,
                product_name="SYSTEM_TEST",
                alert_type="TEST",
                recipient=recipient,
                status="PENDING",
                created_at=datetime.utcnow(),
                retry_count=0
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            log_id = log_entry.id
        except Exception as e:
            logger.error(f"Failed to create NotificationLog for test email: {e}")
            db.close()
            return False, "Failed to record notification log"
        finally:
            db.close()

        # Submit to background executor
        self._executor.submit(
            self._dispatch_email_job,
            log_id,
            recipient,
            subject,
            html_content,
            text_content
        )
        return True, f"Test email queued for delivery to {recipient}"

    def evaluate_and_notify(
        self,
        product: Product,
        db_session = None,
        recipient_override: Optional[str] = None,
        user_id_override: Optional[int] = None
    ) -> Optional[str]:
        """
        Core State Machine:
        Evaluates a product's current validated stock against threshold and triggers
        email notification only on state transitions.
        
        Returns: triggered transition name ('LOW_STOCK', 'OUT_OF_STOCK', 'RESET', None)
        """
        try:
            current_stock = int(product.stock)
            threshold = int(product.threshold if product.threshold is not None else 5)
            current_state = product.notification_state or "NORMAL"

            new_state = current_state
            alert_type = None

            # Evaluate state machine
            if current_stock <= 0:
                if current_state != "OUT_OF_STOCK":
                    new_state = "OUT_OF_STOCK"
                    alert_type = "OUT_OF_STOCK"
            elif current_stock <= threshold:
                if current_state not in ("LOW_STOCK", "OUT_OF_STOCK"):
                    new_state = "LOW_STOCK"
                    alert_type = "LOW_STOCK"
            else:
                # Stock is above threshold -> reset to NORMAL
                if current_state != "NORMAL":
                    new_state = "NORMAL"

            # Update product notification state
            if new_state != current_state:
                product.notification_state = new_state
                # If caller provided db_session, don't commit their transaction, just let it persist
                # or commit if they manage it.
                if db_session:
                    try:
                        db_session.add(product)
                        # We do not commit db_session here to avoid interfering with caller's atomic commit
                    except Exception as e:
                        logger.warning(f"Could not update product notification_state in caller session: {e}")

            # If no alert triggered or reset to normal, return
            if not alert_type:
                return "RESET" if (current_state != "NORMAL" and new_state == "NORMAL") else None

            # Secondary deduplication: check if an alert of this type was logged for this product in the last 2 minutes
            check_db = SessionLocal()
            try:
                recent_window = datetime.utcnow() - timedelta(minutes=2)
                existing_recent = check_db.query(NotificationLog).filter(
                    NotificationLog.product_id == product.id,
                    NotificationLog.alert_type == alert_type,
                    NotificationLog.created_at >= recent_window,
                    NotificationLog.status.in_(["PENDING", "SENT"])
                ).first()
                if existing_recent:
                    logger.info(f"Duplicate alert suppressed for product {product.name} ({alert_type})")
                    return None
            finally:
                check_db.close()

            # Determine recipient strictly from registered users
            recipient = recipient_override
            target_user_id = user_id_override

            if not recipient:
                lookup_db = SessionLocal()
                try:
                    # Find first active admin, or any active registered user with an email
                    user = lookup_db.query(User).filter(
                        User.is_active == True,
                        User.email != None,
                        User.email != ""
                    ).order_by(User.role == "admin").first()
                    if user:
                        recipient = user.email
                        target_user_id = user.id
                finally:
                    lookup_db.close()

            if not recipient:
                # Fallback to configured sender or administrator email in config
                recipient = settings.GMAIL_FROM or settings.GMAIL_USERNAME

            if not recipient or "@" not in recipient:
                logger.warning(f"Cannot dispatch {alert_type} for {product.name}: No valid registered recipient email found.")
                return None

            # Shelf lookup
            shelf_name = "Shelf Main"
            if product.shelf_id:
                shelf_db = SessionLocal()
                try:
                    sh = shelf_db.query(Shelf).filter(Shelf.id == product.shelf_id).first()
                    if sh:
                        shelf_name = sh.name
                finally:
                    shelf_db.close()

            subject, html_content, text_content = render_stock_alert_email(
                product_name=product.name,
                current_stock=current_stock,
                threshold=threshold,
                alert_type=alert_type,
                shelf_name=shelf_name,
                category=product.category or "General",
                sku=product.sku or "N/A"
            )

            # Persist notification log
            log_db = SessionLocal()
            try:
                log_entry = NotificationLog(
                    notification_id=str(uuid.uuid4()),
                    user_id=target_user_id,
                    product_id=product.id,
                    product_name=product.name,
                    alert_type=alert_type,
                    recipient=recipient,
                    status="PENDING",
                    created_at=datetime.utcnow(),
                    retry_count=0
                )
                log_db.add(log_entry)
                log_db.commit()
                log_db.refresh(log_entry)
                log_id = log_entry.id
            except Exception as e:
                logger.error(f"Failed to record NotificationLog for {product.name}: {e}")
                return alert_type
            finally:
                log_db.close()

            # Submit background dispatch
            self._executor.submit(
                self._dispatch_email_job,
                log_id,
                recipient,
                subject,
                html_content,
                text_content
            )
            return alert_type

        except Exception as e:
            # Under NO circumstance should notification failures break inventory updates!
            logger.error(f"Safe exception in evaluate_and_notify for product {getattr(product, 'name', 'unknown')}: {e}", exc_info=True)
            return None


# Global singleton instance
email_service = EmailService()
