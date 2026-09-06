from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from datetime import datetime
import uuid
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String, default="")
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    role = Column(String, default="user")  # "admin", "staff" / "user", "viewer"
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Main Shelf Cam")
    location = Column(String, default="Aisle 1")
    source = Column(String, default="0")  # 0 for webcam, RTSP URL, or video path
    camera_type = Column(String, default="webcam")  # webcam, rtsp, file, demo
    status = Column(String, default="ACTIVE")  # ACTIVE, OFFLINE
    created_at = Column(DateTime, default=datetime.utcnow)


class Shelf(Base):
    __tablename__ = "shelves"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String, default="General")  # Allowed category for misplaced checks
    camera_id = Column(Integer, nullable=True)
    # Normalized ROI coordinates (0.0 to 1.0)
    roi_x1 = Column(Float, default=0.05)
    roi_y1 = Column(Float, default=0.20)
    roi_x2 = Column(Float, default=0.95)
    roi_y2 = Column(Float, default=0.85)
    capacity = Column(Integer, default=20)
    current_count = Column(Integer, default=0)
    status = Column(String, default="NORMAL")  # NORMAL, LOW_STOCK, EMPTY, MISPLACED
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    stock = Column(Integer, default=0)
    expected_stock = Column(Integer, default=20)
    threshold = Column(Integer, default=5)
    price = Column(Float, default=0.0)
    category = Column(String, default="General")
    image_url = Column(String, default="")
    shelf_id = Column(Integer, nullable=True)
    class_id = Column(Integer, nullable=True)  # YOLO class ID mapping
    sku = Column(String, default="")
    notification_state = Column(String, default="NORMAL")  # NORMAL, LOW_STOCK, OUT_OF_STOCK
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, default=lambda: str(uuid.uuid4()), index=True)
    event_type = Column(String, default="PRODUCT_REMOVED", index=True)
    product_name = Column(String, index=True)
    product_id = Column(Integer, nullable=True)
    tracking_id = Column(Integer, nullable=True)
    camera_id = Column(Integer, nullable=True)
    shelf_id = Column(Integer, nullable=True)
    quantity_removed = Column(Integer, default=1)  # Positive for removal, negative for addition
    confidence = Column(Float, default=1.0)
    status = Column(String, default="VERIFIED")  # PENDING, VERIFIED, SUSPICIOUS, FLAGGED
    metadata_json = Column(Text, default="{}")
    timestamp = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    severity = Column(String, default="WARNING")  # INFO, WARNING, HIGH, CRITICAL
    alert_type = Column(String, default="LOW_STOCK")
    product_name = Column(String, index=True)
    shelf_id = Column(Integer, nullable=True)
    tracking_id = Column(Integer, nullable=True)
    message = Column(Text)
    is_resolved = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class AuthAuditLog(Base):
    __tablename__ = "auth_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True)  # LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, PASSWORD_CHANGED, etc.
    username_or_email = Column(String, index=True, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    details = Column(Text, default="")


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, index=True)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, index=True)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, nullable=True, index=True)
    product_id = Column(Integer, nullable=True, index=True)
    product_name = Column(String, nullable=True, index=True)
    alert_type = Column(String, default="LOW_STOCK", index=True)  # LOW_STOCK, OUT_OF_STOCK, TEST
    recipient = Column(String, nullable=False, index=True)
    status = Column(String, default="PENDING", index=True)  # PENDING, SENT, FAILED, RETRYING
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)