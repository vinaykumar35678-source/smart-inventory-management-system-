from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
import os
import base64
import numpy as np
import secrets
import hashlib

from . import models, schemas
from .database import SessionLocal
from .config import settings
from .inventory_logic import process_removal
from .detection import simulate_detection, detect_from_frame
from .websocket import manager
from .notifications.email_service import email_service
from .rate_limiter import (
    record_ip_attempt, check_ip_rate_limit, apply_progressive_delay,
    is_account_locked, record_failed_attempt, reset_failed_attempts,
    timing_safe_dummy_verify
)
from .auth import (
    get_db, get_current_user, require_admin, require_staff_or_admin,
    hash_password, verify_password, validate_password_policy,
    create_access_token, revoke_token, extract_token_from_request,
    log_auth_event
)

router = APIRouter()


# ── Secure Authentication Endpoints ───────────────────────────────────────────

@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(
    req: schemas.LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Secure Login Flow:
    1. Apply IP-based rate limiting & progressive delay.
    2. Normalize identifier and safely look up user via parameterized ORM query.
    3. Check temporary cooldown lockout state.
    4. Constant-time password verification (or timing-safe dummy verification).
    5. Issue JWT session token with unique jti; set HttpOnly SameSite cookie.
    6. Record non-sensitive security audit event.
    """
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    # Apply progressive delay if IP is generating repeated failed requests
    apply_progressive_delay(client_ip)
    record_ip_attempt(client_ip)

    identifier = req.get_identifier()

    # Parameterized ORM search: matches either username or email (case-insensitive for email)
    user = db.query(models.User).filter(
        or_(
            models.User.username == identifier,
            models.User.email == identifier.lower()
        )
    ).first()

    # Check for temporary account lockout
    if user:
        is_locked, remaining_secs = is_account_locked(user)
        if is_locked:
            log_auth_event(
                db=db,
                event_type="ACCOUNT_LOCKED_TEMPORARY",
                username_or_email=identifier,
                request=request,
                details=f"Login attempted while account is throttled ({remaining_secs}s remaining)"
            )
            # Generic error message to prevent user enumeration
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

    # Constant-time evaluation to prevent timing-based enumeration
    if not user:
        timing_safe_dummy_verify(req.password)
        log_auth_event(
            db=db,
            event_type="LOGIN_FAILURE",
            username_or_email=identifier,
            request=request,
            details="User not found (generic rejection)"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # If user exists but is deactivated
    if not user.is_active:
        timing_safe_dummy_verify(req.password)
        log_auth_event(
            db=db,
            event_type="LOGIN_FAILURE",
            username_or_email=identifier,
            request=request,
            details="Inactive account login attempt"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Verify password hash
    is_valid_pw = verify_password(req.password, user.hashed_password)
    if not is_valid_pw:
        became_locked = record_failed_attempt(user, db)
        if became_locked:
            log_auth_event(
                db=db,
                event_type="ACCOUNT_LOCKED_TEMPORARY",
                username_or_email=identifier,
                request=request,
                details=f"Exceeded max failed attempts ({settings.AUTH_COOLDOWN_ATTEMPTS}). Temporary cooldown applied."
            )
        else:
            log_auth_event(
                db=db,
                event_type="LOGIN_FAILURE",
                username_or_email=identifier,
                request=request,
                details=f"Invalid password (attempt #{user.failed_login_attempts})"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Successful authentication
    reset_failed_attempts(user, db)

    # Determine token lifespan based on Remember Me preference
    if req.remember_me:
        expires_delta = timedelta(days=settings.REMEMBER_ME_EXPIRE_DAYS)
    else:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    token, jti, expire_dt = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=expires_delta
    )

    # Issue HttpOnly, SameSite=Lax cookie for browser session defense against XSS token theft
    max_age_seconds = int((expire_dt - datetime.utcnow()).total_seconds())
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=max_age_seconds,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/"
    )

    log_auth_event(
        db=db,
        event_type="LOGIN_SUCCESS",
        username_or_email=user.username,
        request=request,
        details=f"Authenticated as role '{user.role}'"
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name or user.username,
    }


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Invalidates current session on the server by recording token jti into
    the revoked_tokens blocklist, clearing HttpOnly cookies, and logging event.
    """
    token = extract_token_from_request(request)
    username = "unknown"
    if token:
        try:
            from jose import jwt
            payload = jwt.decode(
                token,
                settings.AUTH_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False}
            )
            jti = payload.get("jti")
            username = payload.get("sub", "unknown")
            exp_timestamp = payload.get("exp")
            expires_at = datetime.utcfromtimestamp(exp_timestamp) if exp_timestamp else datetime.utcnow() + timedelta(days=1)
            if jti:
                revoke_token(jti=jti, expires_at=expires_at, db=db)
        except Exception as e:
            print(f"[Logout Token Revocation Note]: {e}")

    # Invalidate browser cookie
    response.delete_cookie(key="access_token", path="/", httponly=True, samesite="lax")

    log_auth_event(
        db=db,
        event_type="LOGOUT",
        username_or_email=username,
        request=request,
        details="User logged out; session revoked."
    )

    return {"message": "Logged out successfully."}


@router.post("/auth/register", response_model=schemas.UserResponse)
def register_user(
    req: schemas.UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public registration endpoint:
    - Authoritative server-side password & email validation
    - Parameterized duplicate check
    - Mass assignment protection (hardcoded 'user' role)
    - Password hashed with bcrypt
    """
    # Authoritative password policy validation
    is_valid_pw, pw_err = validate_password_policy(req.password)
    if not is_valid_pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

    # Check for existing account
    normalized_email = req.email.lower().strip()
    existing = db.query(models.User).filter(
        or_(
            models.User.username == req.username,
            models.User.email == normalized_email
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this username or email already exists."
        )

    hashed = hash_password(req.password)
    new_user = models.User(
        username=req.username,
        full_name=req.full_name or req.username,
        email=normalized_email,
        hashed_password=hashed,
        role="user",  # Strict server-side role assignment; prevents mass assignment privilege escalation
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_auth_event(
        db=db,
        event_type="REGISTER_SUCCESS",
        username_or_email=new_user.username,
        request=request,
        details=f"New user registered: {new_user.username}"
    )

    return new_user


@router.post("/auth/forgot-password")
def forgot_password(
    req: schemas.ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Generates single-use cryptographically secure reset token.
    Returns generic response to prevent email/account enumeration.
    """
    normalized_email = req.email.lower().strip()
    user = db.query(models.User).filter(models.User.email == normalized_email).first()

    if user and user.is_active:
        # Cryptographically secure random token (never returned in HTTP response or logged)
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        user.password_reset_token = token_hash
        user.password_reset_expires = datetime.utcnow() + timedelta(minutes=15)
        db.commit()

        log_auth_event(
            db=db,
            event_type="PASSWORD_RESET_REQUESTED",
            username_or_email=user.username,
            request=request,
            details="Password reset token issued"
        )
        # Development helper: in local dev, log safe notification without token
        print(f"[Password Reset Notice]: Reset token created for user '{user.username}'. Valid for 15 minutes.")
    else:
        # Dummy delay to prevent timing discrepancy
        timing_safe_dummy_verify("timing_check_dummy")

    # Generic response regardless of whether account exists
    return {
        "message": "If an account exists for this email, password reset instructions have been dispatched."
    }


@router.post("/auth/reset-password")
def reset_password(
    req: schemas.ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Validates single-use reset token and updates password securely.
    """
    is_valid_pw, pw_err = validate_password_policy(req.new_password)
    if not is_valid_pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

    token_hash = hashlib.sha256(req.token.encode("utf-8")).hexdigest()
    user = db.query(models.User).filter(models.User.password_reset_token == token_hash).first()

    if not user or not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or previously used password reset token."
        )

    user.hashed_password = hash_password(req.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = datetime.utcnow()
    db.commit()

    log_auth_event(
        db=db,
        event_type="PASSWORD_RESET_COMPLETED",
        username_or_email=user.username,
        request=request,
        details="Password successfully reset via recovery token."
    )

    return {"message": "Password successfully updated. Please sign in with your new credentials."}


@router.post("/auth/change-password")
def change_password(
    req: schemas.ChangePasswordRequest,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows authenticated user to change password after verifying their current password.
    """
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed."
        )

    is_valid_pw, pw_err = validate_password_policy(req.new_password)
    if not is_valid_pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

    current_user.hashed_password = hash_password(req.new_password)
    current_user.updated_at = datetime.utcnow()

    # Revoke current token
    current_jti = getattr(request.state, "current_jti", None)
    if current_jti:
        revoke_token(current_jti, datetime.utcnow() + timedelta(days=1), db)

    db.commit()

    log_auth_event(
        db=db,
        event_type="PASSWORD_CHANGED",
        username_or_email=current_user.username,
        request=request,
        details="User voluntarily changed password."
    )

    return {"message": "Password updated successfully. Please log in again."}


@router.get("/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Returns current authenticated user details.
    """
    return current_user


@router.get("/auth/audit-logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin)
):
    """
    View authentication and security audit events (Admin only).
    """
    safe_limit = min(max(limit, 1), 100)
    logs = (
        db.query(models.AuthAuditLog)
        .order_by(desc(models.AuthAuditLog.timestamp))
        .offset(offset)
        .limit(safe_limit)
        .all()
    )
    return logs


# ── User Management (Admin only) ──────────────────────────────────────────────

@router.get("/users", response_model=List[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin)
):
    return db.query(models.User).all()


@router.post("/users", response_model=schemas.UserResponse)
def create_user(
    user_in: schemas.UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    # Validate password policy
    is_valid_pw, pw_err = validate_password_policy(user_in.password)
    if not is_valid_pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

    existing = db.query(models.User).filter(models.User.username == user_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    assigned_role = user_in.role if user_in.role in ("admin", "user", "staff", "viewer") else "user"
    new_user = models.User(
        username=user_in.username,
        full_name=user_in.full_name or user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=assigned_role,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_auth_event(
        db=db,
        event_type="USER_CREATED_BY_ADMIN",
        username_or_email=new_user.username,
        request=request,
        details=f"Admin '{_admin.username}' created user '{new_user.username}' with role '{assigned_role}'"
    )
    return new_user


@router.put("/users/{user_id}/toggle", response_model=schemas.UserResponse)
def toggle_user_active(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot deactivate primary admin account")
    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    log_auth_event(
        db=db,
        event_type="USER_STATUS_TOGGLED",
        username_or_email=user.username,
        request=request,
        details=f"Admin '{_admin.username}' set status to active={user.is_active}"
    )
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete primary admin account")

    deleted_username = user.username
    db.delete(user)
    db.commit()

    log_auth_event(
        db=db,
        event_type="USER_DELETED",
        username_or_email=deleted_username,
        request=request,
        details=f"Admin '{_admin.username}' deleted user '{deleted_username}'"
    )
    return {"message": f"User '{deleted_username}' deleted"}


# ── Webcam Frame Analysis ─────────────────────────────────────────────────────


@router.post("/detect/frame")
async def detect_webcam_frame(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Accepts a base64-encoded JPEG/PNG frame from browser webcam / uploaded video.
    Runs the advanced Computer Vision pipeline (Detection -> ByteTrack -> Pose -> Shelf ROI -> Behavior).
    """
    import asyncio, cv2
    from concurrent.futures import ThreadPoolExecutor
    from .ai.pipeline import pipeline

    # ── Decode image ────────────────────────────────────────
    try:
        img_data = payload.get("image", "")
        if not img_data:
            return {"error": "No image provided", "detected": [], "tracked_objects": [], "shelves": {}, "persons_detected": 0}

        # Strip data-URL prefix e.g. "data:image/jpeg;base64,..."
        if "," in img_data:
            img_data = img_data.split(",", 1)[1]

        img_bytes = base64.b64decode(img_data)
        np_arr    = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return {"error": "Could not decode image", "detected": [], "tracked_objects": [], "shelves": {}, "persons_detected": 0}

    except Exception as e:
        return {"error": f"Image decode error: {e}", "detected": [], "tracked_objects": [], "shelves": {}, "persons_detected": 0}

    # ── Run Vision Pipeline in thread pool ───────────────────
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=1) as pool:
            cv_res = await loop.run_in_executor(pool, pipeline.process_frame, frame, db)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": f"Pipeline processing error: {e}",
            "detected": [],
            "tracked_objects": [],
            "tracked_count": 0,
            "shelves": {},
            "misplaced_items": [],
            "pose_results": [],
            "events": [],
            "pending_events": 0,
            "system_status": "NORMAL",
            "persons_detected": 0,
            "fps": 0.0,
            "latency_ms": 0.0,
            "device": "CPU",
            "model_name": "YOLO"
        }

    tracked_objects = cv_res.get("tracked_objects", [])
    seen_persons = len([t for t in tracked_objects if t.get("category") == "person"])
    events = cv_res.get("events", [])

    # Format backwards-compatible detected results for older UI listeners
    backwards_compatible = []
    for ev in events:
        backwards_compatible.append({
            "type": "removal" if ev.get("event_type") in ("PRODUCT_REMOVED", "SUSPICIOUS_REMOVAL") else "addition",
            "product": ev.get("product"),
            "quantity": ev.get("quantity", 1),
            "confidence": ev.get("confidence", 0.9),
            "timestamp": ev.get("timestamp", datetime.utcnow().isoformat()),
            "stock": ev.get("stock")
        })

    if seen_persons > 0:
        backwards_compatible.append({
            "type": "person",
            "label": "Person",
            "message": f"👤 {seen_persons} person(s) near shelf area",
            "confidence": 0.95,
            "timestamp": datetime.utcnow().isoformat()
        })

    return {
        "detected": backwards_compatible,
        "tracked_objects": tracked_objects,
        "tracked_count": cv_res.get("tracked_count", 0),
        "shelves": cv_res.get("shelves", {}),
        "misplaced_items": cv_res.get("misplaced_items", []),
        "pose_results": cv_res.get("pose_results", []),
        "events": events,
        "pending_events": cv_res.get("pending_events", 0),
        "system_status": cv_res.get("system_status", "NORMAL"),
        "persons_detected": seen_persons,
        "fps": cv_res.get("fps", 0.0),
        "latency_ms": cv_res.get("latency_ms", 0.0),
        "device": cv_res.get("device", "CPU"),
        "model_name": cv_res.get("model_name", "YOLO")
    }


# ── Products ──────────────────────────────────────────────────────────────────


@router.get("/products", response_model=List[schemas.ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    return db.query(models.Product).all()


@router.get("/products/{product_id}", response_model=schemas.ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/products", response_model=schemas.ProductResponse)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    existing = db.query(models.Product).filter(models.Product.name == product.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    db_product = models.Product(**product.dict(), created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.put("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    update: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in update.dict(exclude_unset=True).items():
        setattr(product, field, value)
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)

    # Evaluate inventory state machine for low/out-of-stock notification
    try:
        email_service.evaluate_and_notify(product, db_session=db)
    except Exception as e:
        print(f"[Product Update Notification Note]: {e}")

    return product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": f"Product '{product.name}' deleted successfully"}


# ── Events ────────────────────────────────────────────────────────────────────

@router.get("/events", response_model=List[schemas.EventResponse])
def get_events(
    limit: int = 50,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    return db.query(models.Event).order_by(models.Event.timestamp.desc()).limit(limit).all()


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=List[schemas.AlertResponse])
def get_alerts(
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    return db.query(models.Alert).order_by(models.Alert.timestamp.desc()).all()


@router.post("/alerts/{alert_id}/resolve", response_model=schemas.AlertResponse)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert


# ── Simulate Detection ────────────────────────────────────────────────────────

@router.post("/detect/simulate")
def trigger_simulation(
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    detected = simulate_detection()
    results = []
    for product_name, info in detected.items():
        qty = info.get("quantity", 1)
        conf = info.get("confidence", 0.95)
        product = db.query(models.Product).filter(models.Product.name == product_name).first()
        if product:
            result = process_removal(product_name, qty, conf, db)
            results.append(result)
        else:
            event = models.Event(product_name=product_name, quantity_removed=qty, confidence=conf)
            db.add(event)
            db.commit()
            results.append({
                "type": "removal", "product": product_name, "quantity": qty,
                "confidence": conf, "timestamp": datetime.utcnow().isoformat(), "stock": None
            })
    return {"detected": results}


# ── Export Excel ──────────────────────────────────────────────────────────────

@router.get("/export/excel")
def export_excel(
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    products = db.query(models.Product).all()
    data = [
        {
            "ID": p.id, "Name": p.name, "Category": p.category,
            "Stock": p.stock, "Threshold": p.threshold, "Price (Rs)": p.price,
            "Status": "Low Stock" if p.stock <= p.threshold else "OK",
            "Last Updated": p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else ""
        }
        for p in products
    ]
    df = pd.DataFrame(data)
    export_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "inventory_export.xlsx"))
    with pd.ExcelWriter(export_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory")
    return FileResponse(
        export_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="inventory_export.xlsx"
    )


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    total_products = db.query(models.Product).count()
    low_stock = db.query(models.Product).filter(
        models.Product.stock <= models.Product.threshold
    ).count()
    total_events = db.query(models.Event).count()
    unresolved_alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).count()
    return {
        "total_products": total_products,
        "low_stock_count": low_stock,
        "total_events_today": total_events,
        "unresolved_alerts": unresolved_alerts,
    }


# ── Shelves / Zones ───────────────────────────────────────────────────────────

@router.get("/shelves", response_model=List[schemas.ShelfResponse])
def get_shelves(
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    return db.query(models.Shelf).all()


@router.post("/shelves", response_model=schemas.ShelfResponse)
def create_shelf(
    shelf_in: schemas.ShelfCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    existing = db.query(models.Shelf).filter(models.Shelf.name == shelf_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Shelf with this name already exists")
    new_shelf = models.Shelf(**shelf_in.dict(), created_at=datetime.utcnow())
    db.add(new_shelf)
    db.commit()
    db.refresh(new_shelf)
    return new_shelf


@router.put("/shelves/{shelf_id}", response_model=schemas.ShelfResponse)
def update_shelf(
    shelf_id: int,
    shelf_update: schemas.ShelfUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    shelf = db.query(models.Shelf).filter(models.Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="Shelf not found")
    for field, val in shelf_update.dict(exclude_unset=True).items():
        setattr(shelf, field, val)
    db.commit()
    db.refresh(shelf)
    return shelf


@router.delete("/shelves/{shelf_id}")
def delete_shelf(
    shelf_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    shelf = db.query(models.Shelf).filter(models.Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="Shelf not found")
    db.delete(shelf)
    db.commit()
    return {"message": f"Shelf '{shelf.name}' deleted"}


# ── Cameras ───────────────────────────────────────────────────────────────────

@router.get("/cameras", response_model=List[schemas.CameraResponse])
def get_cameras(
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    return db.query(models.Camera).all()


@router.post("/cameras", response_model=schemas.CameraResponse)
def create_camera(
    camera_in: schemas.CameraCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    new_cam = models.Camera(**camera_in.dict(), created_at=datetime.utcnow())
    db.add(new_cam)
    db.commit()
    db.refresh(new_cam)
    return new_cam


@router.put("/cameras/{camera_id}", response_model=schemas.CameraResponse)
def update_camera(
    camera_id: int,
    cam_update: schemas.CameraUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    for field, val in cam_update.dict(exclude_unset=True).items():
        setattr(cam, field, val)
    db.commit()
    db.refresh(cam)
    return cam


@router.delete("/cameras/{camera_id}")
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(cam)
    db.commit()
    return {"message": f"Camera '{cam.name}' deleted"}


# ── AI Model Status & Thresholds ──────────────────────────────────────────────

@router.get("/detection/status", response_model=schemas.AIStatusResponse)
def get_detection_status(_user: models.User = Depends(get_current_user)):
    from .ai.pipeline import pipeline
    from .ai.detection.detector import detector
    from .ai.tracking.tracker import tracker
    info = detector.get_info()
    return {
        "model_name": info["model_name"],
        "version": "YOLOv8/11 + ByteTrack",
        "device": info["device"],
        "fps": pipeline.current_fps,
        "inference_time_ms": pipeline.last_inference_ms,
        "tracked_objects": len(tracker.tracks),
        "active_camera": pipeline.active_camera,
        "detection_status": "RUNNING" if pipeline.is_running else "PAUSED",
        "classes_count": info["classes_count"]
    }


@router.post("/detection/start")
def start_detection(_user: models.User = Depends(require_staff_or_admin)):
    from .ai.pipeline import pipeline
    pipeline.is_running = True
    return {"status": "RUNNING", "message": "AI Vision Pipeline active"}


@router.post("/detection/stop")
def stop_detection(_user: models.User = Depends(require_staff_or_admin)):
    from .ai.pipeline import pipeline
    pipeline.is_running = False
    return {"status": "PAUSED", "message": "AI Vision Pipeline paused"}


@router.get("/settings/thresholds")
def get_thresholds(_user: models.User = Depends(get_current_user)):
    from .ai.config.config import ai_config
    return ai_config.as_dict()


@router.put("/settings/thresholds")
def update_thresholds(
    thresholds: dict,
    _admin: models.User = Depends(require_admin)
):
    from .ai.config.config import ai_config
    ai_config.update(thresholds)
    return {"message": "Thresholds updated successfully", "config": ai_config.as_dict()}


# ── Advanced Inventory Analytics ──────────────────────────────────────────────

@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    from sqlalchemy import func
    products = db.query(models.Product).all()
    shelves = db.query(models.Shelf).all()
    events = db.query(models.Event).all()
    alerts = db.query(models.Alert).all()

    total_stock = sum(p.stock for p in products)
    low_stock = sum(1 for p in products if p.stock <= p.threshold)
    out_of_stock = sum(1 for p in products if p.stock == 0)

    # Category breakdown
    categories_stock = {}
    for p in products:
        categories_stock[p.category] = categories_stock.get(p.category, 0) + p.stock

    # Top removed products
    removals_by_product = {}
    removals_count = 0
    additions_count = 0
    suspicious_count = 0
    misplaced_count = 0

    for ev in events:
        qty = abs(ev.quantity_removed or 1)
        if ev.event_type in ("PRODUCT_REMOVED", "SUSPICIOUS_REMOVAL") or (ev.quantity_removed and ev.quantity_removed > 0):
            removals_count += qty
            removals_by_product[ev.product_name] = removals_by_product.get(ev.product_name, 0) + qty
        if ev.event_type in ("PRODUCT_PLACED", "RESTOCKING_DETECTED") or (ev.quantity_removed and ev.quantity_removed < 0):
            additions_count += qty
        if ev.event_type == "SUSPICIOUS_REMOVAL" or ev.status == "SUSPICIOUS":
            suspicious_count += 1
        if ev.event_type == "PRODUCT_MISPLACED":
            misplaced_count += 1

    top_removed = [
        {"product": k, "count": v}
        for k, v in sorted(removals_by_product.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    # Shelf occupancy / utilization
    shelf_utilization = []
    for s in shelves:
        pct = round((s.current_count / max(1, s.capacity)) * 100, 1)
        shelf_utilization.append({
            "shelf_id": s.id,
            "name": s.name,
            "category": s.category,
            "current_count": s.current_count,
            "capacity": s.capacity,
            "utilization_pct": pct,
            "status": s.status
        })

    # Loss prevention alerts summary
    suspicious_alerts = [
        {
            "id": a.id,
            "product": a.product_name,
            "message": a.message,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "is_resolved": a.is_resolved
        }
        for a in alerts if a.severity in ("HIGH", "CRITICAL") or "LOSS PREVENTION" in (a.message or "")
    ][:10]

    return {
        "total_products": len(products),
        "total_stock": total_stock,
        "low_stock_count": low_stock,
        "out_of_stock_count": out_of_stock,
        "total_removals": removals_count,
        "total_additions": additions_count,
        "suspicious_incidents_count": suspicious_count,
        "misplaced_count": misplaced_count,
        "category_distribution": [{"category": k, "stock": v} for k, v in categories_stock.items()],
        "top_removed_products": top_removed,
        "shelf_utilization": shelf_utilization,
        "recent_suspicious_incidents": suspicious_alerts
    }


# ── College Project Viva Demo Scenarios ───────────────────────────────────────

@router.post("/demo/scenario/{scenario_name}")
def trigger_demo_scenario(
    scenario_name: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    """
    Triggers simulated real-time CV scenarios for evaluation/demonstration without physical CCTV.
    Scenarios:
      - 'restock': Restocks items, creates PRODUCT_PLACED event, increments stock.
      - 'pickup': Customer picks up product, creates verified PRODUCT_REMOVED event, decrements stock.
      - 'misplaced': Item placed in wrong shelf category, triggers PRODUCT_MISPLACED alert.
      - 'suspicious_removal': Rapid removal without checkout, triggers loss-prevention alert.
    """
    from .ai.events.event_engine import event_engine
    import random

    if scenario_name == "restock":
        product = db.query(models.Product).filter(models.Product.name == "Milk (1L)").first() or db.query(models.Product).first()
        if not product:
            raise HTTPException(status_code=400, detail="No product available")
        ev = {
            "event_type": "PRODUCT_PLACED",
            "product_name": product.name,
            "tracking_id": random.randint(10, 99),
            "shelf_id": product.shelf_id or 1,
            "quantity": 2,
            "confidence": 0.96,
            "status": "VERIFIED",
            "metadata": {"action": "RESTOCKING_DETECTED", "inside_frames": 15}
        }
        res = event_engine.process_event(ev, db)
        return {"status": "SUCCESS", "scenario": "Restocking Detected", "event": res}

    elif scenario_name == "pickup":
        product = db.query(models.Product).filter(models.Product.name == "Apple").first() or db.query(models.Product).first()
        if not product:
            raise HTTPException(status_code=400, detail="No product available")
        ev = {
            "event_type": "PRODUCT_REMOVED",
            "product_name": product.name,
            "tracking_id": random.randint(10, 99),
            "shelf_id": product.shelf_id or 1,
            "quantity": 1,
            "confidence": 0.94,
            "status": "VERIFIED",
            "metadata": {"person_track_id": 12, "suspicious_score": 40, "outside_frames": 12}
        }
        res = event_engine.process_event(ev, db)
        return {"status": "SUCCESS", "scenario": "Customer Pickup", "event": res}

    elif scenario_name == "misplaced":
        ev = {
            "event_type": "PRODUCT_MISPLACED",
            "product_name": "Lays",
            "tracking_id": random.randint(10, 99),
            "shelf_id": 2,
            "quantity": 1,
            "confidence": 0.91,
            "status": "FLAGGED",
            "metadata": {"expected_category": "Snacks", "detected_shelf": "Shelf 2 - Dairy & Essentials"}
        }
        res = event_engine.process_event(ev, db)
        return {"status": "SUCCESS", "scenario": "Misplaced Product Detected", "event": res}

    elif scenario_name == "suspicious_removal":
        product = db.query(models.Product).filter(models.Product.name == "Mobile Phone").first() or db.query(models.Product).first()
        if not product:
            raise HTTPException(status_code=400, detail="No product available")
        ev = {
            "event_type": "SUSPICIOUS_REMOVAL",
            "product_name": product.name,
            "tracking_id": random.randint(10, 99),
            "shelf_id": product.shelf_id or 3,
            "quantity": 1,
            "confidence": 0.97,
            "status": "SUSPICIOUS",
            "metadata": {
                "person_track_id": 7,
                "suspicious_score": 85,
                "reason": "Rapid unverified removal outside shelf zone"
            }
        }
        res = event_engine.process_event(ev, db)
        return {"status": "SUCCESS", "scenario": "Loss Prevention Alert Triggered", "event": res}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario_name}'")


# =========================================================
# ML DATASET IMPORT, VALIDATION & TRAINING ENDPOINTS
# =========================================================
import json
import threading
from ml.scripts.dataset_manager import dataset_manager
from ml.scripts.model_manager import model_manager
from ml.training.train import run_custom_training, get_current_progress, CONFIG_FILE
from .schemas import DatasetImportRequest, DatasetValidateRequest, TrainingLaunchRequest, ModelTestRequest

@router.get("/ml/datasets")
def list_ml_datasets(current_user: models.User = Depends(get_current_user)):
    """List available datasets in ml/datasets and existing project directories."""
    return dataset_manager.list_datasets()

@router.post("/ml/datasets/import")
def import_ml_dataset(
    req: DatasetImportRequest,
    current_user: models.User = Depends(require_admin)
):
    """Import dataset from local folder, ZIP file, or existing directory."""
    try:
        if req.source_type == "zip":
            res = dataset_manager.import_from_zip(req.source_path, req.dataset_name)
        else:
            res = dataset_manager.import_from_directory(req.source_path, req.dataset_name)
        return {"status": "SUCCESS", "dataset": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ml/datasets/validate")
def validate_ml_dataset(
    req: DatasetValidateRequest,
    current_user: models.User = Depends(get_current_user)
):
    """Validate YOLO dataset annotations, detect corrupt images, and calculate class distribution."""
    try:
        report = dataset_manager.validate_dataset(req.dataset_path, req.yaml_path)
        return report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ml/datasets/preview")
def preview_ml_dataset(
    dataset_path: str,
    max_samples: int = 6,
    current_user: models.User = Depends(get_current_user)
):
    """Return visual annotated image previews with bounding boxes overlaid."""
    try:
        previews = dataset_manager.generate_previews(dataset_path, max_samples=max_samples)
        return {"previews": previews}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ml/training/config")
def get_training_config(current_user: models.User = Depends(get_current_user)):
    """Get centralized training configuration."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"model_type": "yolov8n.pt", "epochs": 20, "batch_size": 8, "image_size": 640}

@router.put("/ml/training/config")
def update_training_config(
    new_config: Dict[str, Any],
    current_user: models.User = Depends(require_admin)
):
    """Update training parameters."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=2)
    return {"status": "SUCCESS", "config": new_config}

@router.post("/ml/training/start")
def start_custom_training(
    req: TrainingLaunchRequest,
    current_user: models.User = Depends(require_admin)
):
    """Launch custom YOLO training in a background worker thread."""
    prog = get_current_progress()
    if prog.get("status") == "TRAINING":
        raise HTTPException(status_code=409, detail="A training job is already in progress.")

    # Validate YAML path
    if not os.path.exists(req.data_yaml):
        raise HTTPException(status_code=404, detail=f"data.yaml not found at {req.data_yaml}")

    def _train_worker():
        try:
            run_custom_training(
                data_yaml=req.data_yaml,
                base_model=req.base_model,
                epochs=req.epochs,
                batch_size=req.batch_size,
                image_size=req.image_size,
                model_name=req.model_name,
                dataset_name=req.dataset_name
            )
        except Exception as err:
            print(f"[Training Thread ERROR] {err}")

    thread = threading.Thread(target=_train_worker, daemon=True)
    thread.start()

    return {"status": "TRAINING_LAUNCHED", "message": f"Training job launched for {req.model_name or 'model'}"}

@router.get("/ml/training/status")
def get_training_status(current_user: models.User = Depends(get_current_user)):
    """Poll real-time per-epoch metrics (epoch, loss, precision, recall, mAP50, mAP50-95)."""
    return get_current_progress()

@router.get("/ml/models")
def list_ml_models(current_user: models.User = Depends(get_current_user)):
    """List all pretrained and custom-trained YOLO models with their metrics."""
    return model_manager.list_models()

@router.post("/ml/models/{model_id}/activate")
def activate_ml_model(
    model_id: str,
    current_user: models.User = Depends(require_admin)
):
    """Set active model for the real-time detection pipeline."""
    try:
        active_record = model_manager.activate_model(model_id)
        return {"status": "SUCCESS", "active_model": active_record}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ml/models/test")
def test_ml_model(
    req: ModelTestRequest,
    current_user: models.User = Depends(get_current_user)
):
    """Test model on single image and return bounding boxes + mapped product name."""
    try:
        res = model_manager.test_model(
            model_id=req.model_id,
            image_data_base64=req.image,
            conf_threshold=req.confidence or 0.35
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ml/models/compare")
def compare_ml_models(current_user: models.User = Depends(get_current_user)):
    """Compare performance metrics between pretrained and custom-trained models."""
    return model_manager.compare_models()


# ── Gmail / SMTP Notifications Endpoints ─────────────────────────────────────

@router.get("/notifications/status", response_model=schemas.NotificationStatusResponse)
def get_notification_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns current notification service status.
    Strictly masks sensitive credentials and provides the registered recipient.
    """
    status_data = email_service.get_status()
    recipient = current_user.email or settings.GMAIL_FROM or settings.GMAIL_USERNAME or ""
    status_data["registered_recipient"] = recipient
    return status_data


@router.post("/notifications/test", response_model=schemas.TestEmailResponse)
def send_test_notification(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Triggers a test email delivery to the authenticated user's registered email address.
    Strictly uses current_user.email to prevent arbitrary recipient abuse.
    """
    recipient = current_user.email
    if not recipient or "@" not in recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your user account does not have a valid registered email address configured."
        )

    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is not configured. Please configure GMAIL_USERNAME and GMAIL_APP_PASSWORD in backend/.env."
        )

    enqueued, msg = email_service.send_test_email(recipient=recipient, user_id=current_user.id)
    if not enqueued:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg
        )

    return {
        "status": "QUEUED",
        "message": msg,
        "recipient": recipient
    }


@router.get("/notifications/history", response_model=List[schemas.NotificationLogResponse])
def get_notification_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns recent notification dispatch audit history.
    """
    safe_limit = min(max(limit, 1), 100)
    query = db.query(models.NotificationLog)
    if current_user.role != "admin":
        query = query.filter(
            or_(
                models.NotificationLog.user_id == current_user.id,
                models.NotificationLog.recipient == current_user.email
            )
        )
    logs = query.order_by(models.NotificationLog.created_at.desc()).offset(offset).limit(safe_limit).all()
    return logs

