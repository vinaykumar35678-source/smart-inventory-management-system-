import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import SessionLocal
from .config import settings
from . import models

# OAuth2 scheme with auto_error=False to allow checking cookie first
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Password Policy & Hashing ─────────────────────────────────────────────────

def validate_password_policy(password: str) -> Tuple[bool, str]:
    """
    Authoritative server-side password validation.
    Enforces minimum 12 characters, max 128 characters, allowing passphrases.
    """
    if not password or len(password) < 12:
        return False, "Password must be at least 12 characters in length."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    return True, ""


def hash_password(password: str) -> str:
    """
    Hash a password securely using bcrypt with 12 salt rounds.
    Safely encodes utf-8 and handles bcrypt 72-byte ceiling.
    """
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Safely verify a plain text password against a stored bcrypt hash.
    Constant-time comparison via bcrypt.checkpw.
    """
    if not plain or not hashed:
        return False
    try:
        pw_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hashed_bytes)
    except Exception:
        return False


# ── JWT Session Management ───────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    custom_jti: Optional[str] = None
) -> Tuple[str, str, datetime]:
    """
    Creates a signed JWT access token embedding jti, sub, role, and expiration.
    Returns: (token_str, jti_str, expire_datetime)
    """
    to_encode = data.copy()
    jti = custom_jti or str(uuid.uuid4())
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    
    to_encode.update({
        "jti": jti,
        "iat": now,
        "exp": expire,
    })
    
    token = jwt.encode(to_encode, settings.AUTH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expire


def is_token_revoked(jti: str, db: Session) -> bool:
    """
    Check if the token jti is in the revoked_tokens blocklist.
    """
    if not jti:
        return True
    revoked = db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first()
    return revoked is not None


def revoke_token(jti: str, expires_at: datetime, db: Session):
    """
    Add a token jti to the revoked_tokens table.
    """
    if not jti:
        return
    existing = db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first()
    if not existing:
        db_revoked = models.RevokedToken(
            jti=jti,
            revoked_at=datetime.utcnow(),
            expires_at=expires_at
        )
        db.add(db_revoked)
        db.commit()


# ── Authentication Middleware & Dependencies ──────────────────────────────────

def extract_token_from_request(request: Request, header_token: Optional[str] = None) -> Optional[str]:
    """
    Extract token from:
    1. Authorization Bearer header (if present)
    2. HttpOnly cookie named 'access_token' (fallback for browser sessions)
    """
    if header_token:
        return header_token
    # Try Authorization header directly
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    # Try cookies
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    return None


def get_current_user(
    request: Request,
    header_token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Authenticate request via cookie or Bearer header, verify signature,
    validate against token revocation blocklist, and ensure user is active.
    """
    token = extract_token_from_request(request, header_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token.")

    # Check server-side revocation list
    if jti and is_token_revoked(jti, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been terminated. Please log in again."
        )

    # Safe parameterized query for user
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated.")

    # Attach token payload metadata to request state if needed
    request.state.current_jti = jti
    request.state.current_user = user
    return user


# ── Role-Based Access Control (RBAC) ──────────────────────────────────────────

def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Authorize user only if role is 'admin'.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource."
        )
    return current_user


def require_staff_or_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Authorize user if role is 'admin', 'staff', or 'user'.
    """
    if current_user.role not in ("admin", "staff", "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or administrator access required."
        )
    return current_user


# ── Audit Logging Helper ──────────────────────────────────────────────────────

def log_auth_event(
    db: Session,
    event_type: str,
    username_or_email: Optional[str],
    request: Request,
    details: str = ""
):
    """
    Record an authentication security event.
    NEVER logs passwords, password hashes, or sensitive secret tokens.
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        # Check for X-Forwarded-For if behind a reverse proxy
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        user_agent = request.headers.get("user-agent", "")[:255]

        audit = models.AuthAuditLog(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            username_or_email=(username_or_email or "anonymous")[:128],
            ip_address=client_ip[:64],
            user_agent=user_agent,
            details=details[:500],
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        # Never fail a request just because audit logging had an issue; print error
        print(f"[Audit Log Error]: {e}")
