from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Auth / Users ──────────────────────────────────────────
class LoginRequest(BaseModel):
    username_or_email: Optional[str] = Field(None, max_length=254)
    username: Optional[str] = Field(None, max_length=254)
    password: str = Field(..., max_length=128)
    remember_me: Optional[bool] = False

    @model_validator(mode="after")
    def check_identifier(self):
        ident = self.username_or_email or self.username
        if not ident or not ident.strip():
            raise ValueError("Email or username is required.")
        return self

    def get_identifier(self) -> str:
        return (self.username_or_email or self.username or "").strip()


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=12, max_length=128)
    full_name: Optional[str] = Field("", max_length=128)
    # Mass assignment protection: role cannot be set by client during registration


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., max_length=254)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=256)
    new_password: str = Field(..., min_length=12, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    full_name: Optional[str] = Field("", max_length=128)
    email: Optional[str] = Field(None, max_length=254)
    password: str = Field(..., min_length=12, max_length=128)
    role: Optional[str] = Field("user", max_length=20)


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    username_or_email: Optional[str]
    ip_address: Optional[str]
    details: Optional[str]

    class Config:
        from_attributes = True


# ── Cameras ───────────────────────────────────────────────
class CameraCreate(BaseModel):
    name: str
    location: Optional[str] = "Aisle 1"
    source: Optional[str] = "0"
    camera_type: Optional[str] = "webcam"
    status: Optional[str] = "ACTIVE"

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    camera_type: Optional[str] = None
    status: Optional[str] = None

class CameraResponse(CameraCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Shelves / Zones ───────────────────────────────────────
class ShelfCreate(BaseModel):
    name: str
    category: Optional[str] = "General"
    camera_id: Optional[int] = None
    roi_x1: Optional[float] = 0.05
    roi_y1: Optional[float] = 0.20
    roi_x2: Optional[float] = 0.95
    roi_y2: Optional[float] = 0.85
    capacity: Optional[int] = 20
    current_count: Optional[int] = 0
    status: Optional[str] = "NORMAL"

class ShelfUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    camera_id: Optional[int] = None
    roi_x1: Optional[float] = None
    roi_y1: Optional[float] = None
    roi_x2: Optional[float] = None
    roi_y2: Optional[float] = None
    capacity: Optional[int] = None
    current_count: Optional[int] = None
    status: Optional[str] = None

class ShelfResponse(ShelfCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Product ──────────────────────────────────────────────
class ProductCreate(BaseModel):
    name: str
    stock: int
    expected_stock: Optional[int] = 20
    threshold: int
    price: float
    category: Optional[str] = "General"
    image_url: Optional[str] = ""
    shelf_id: Optional[int] = None
    class_id: Optional[int] = None
    sku: Optional[str] = ""

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    stock: Optional[int] = None
    expected_stock: Optional[int] = None
    threshold: Optional[int] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    shelf_id: Optional[int] = None
    class_id: Optional[int] = None
    sku: Optional[str] = None
    notification_state: Optional[str] = None

class ProductResponse(ProductCreate):
    id: int
    notification_state: Optional[str] = "NORMAL"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Event ────────────────────────────────────────────────
class EventResponse(BaseModel):
    id: int
    event_id: Optional[str] = None
    event_type: Optional[str] = "PRODUCT_REMOVED"
    product_name: str
    product_id: Optional[int] = None
    tracking_id: Optional[int] = None
    camera_id: Optional[int] = None
    shelf_id: Optional[int] = None
    quantity_removed: int
    confidence: float
    status: Optional[str] = "VERIFIED"
    metadata_json: Optional[str] = "{}"
    timestamp: datetime

    class Config:
        from_attributes = True


# ── Alert ────────────────────────────────────────────────
class AlertResponse(BaseModel):
    id: int
    severity: Optional[str] = "WARNING"
    alert_type: Optional[str] = "LOW_STOCK"
    product_name: str
    shelf_id: Optional[int] = None
    tracking_id: Optional[int] = None
    message: str
    is_resolved: bool
    timestamp: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Thresholds & Configuration ───────────────────────────
class ThresholdsConfig(BaseModel):
    detection_confidence: float = 0.50
    iou_threshold: float = 0.45
    removal_confirmation_frames: int = 15
    placement_confirmation_frames: int = 15
    suspicious_score_threshold: int = 70
    frame_skip: int = 1
    input_size: int = 640


# ── AI Status ────────────────────────────────────────────
class AIStatusResponse(BaseModel):
    model_name: str
    version: str
    device: str
    fps: float
    inference_time_ms: float
    tracked_objects: int
    active_camera: str
    detection_status: str
    classes_count: int


# ── ML Training & Dataset Schemas ────────────────────────
class DatasetImportRequest(BaseModel):
    source_type: str = "existing"
    source_path: str
    dataset_name: str

class DatasetValidateRequest(BaseModel):
    dataset_path: str
    yaml_path: Optional[str] = None

class TrainingLaunchRequest(BaseModel):
    data_yaml: str
    base_model: str = "yolov8n.pt"
    epochs: int = 20
    batch_size: int = 8
    image_size: int = 640
    model_name: Optional[str] = None
    dataset_name: str = "custom_inventory"

class ModelTestRequest(BaseModel):
    model_id: str
    image: str
    confidence: Optional[float] = 0.35

DatasetImportRequest.model_rebuild()
DatasetValidateRequest.model_rebuild()
TrainingLaunchRequest.model_rebuild()
ModelTestRequest.model_rebuild()


# ── Notifications ─────────────────────────────────────────
class NotificationStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    smtp_host: str
    smtp_port: int
    sender_masked: str
    use_tls: bool
    registered_recipient: Optional[str] = None

class TestEmailResponse(BaseModel):
    status: str
    message: str
    recipient: str

class NotificationLogResponse(BaseModel):
    id: int
    notification_id: str
    user_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    alert_type: str
    recipient: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int

    class Config:
        from_attributes = True
