import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import bcrypt

from .config import settings
from . import models

# Thread-safe in-memory store for IP attempt tracking:
# ip -> list of timestamps
_ip_attempts: Dict[str, list] = {}
_lock = threading.Lock()

# Pre-computed dummy hash for constant-time verification when user is not found
DUMMY_HASH = bcrypt.hashpw(
    b"timing_attack_mitigation_safe_dummy_password",
    bcrypt.gensalt(rounds=12)
).decode("utf-8")


def record_ip_attempt(ip: str) -> int:
    """
    Record a login attempt from an IP and return the count of recent attempts
    within the configured rate limit window. Cleans up stale attempts.
    """
    now = time.time()
    cutoff = now - settings.AUTH_RATE_LIMIT_WINDOW

    with _lock:
        if ip not in _ip_attempts:
            _ip_attempts[ip] = []
        # Filter attempts within current window
        _ip_attempts[ip] = [t for t in _ip_attempts[ip] if t > cutoff]
        _ip_attempts[ip].append(now)
        count = len(_ip_attempts[ip])

    return count


def check_ip_rate_limit(ip: str) -> Tuple[bool, float]:
    """
    Check if IP has exceeded thresholds.
    Returns: (is_throttled, progressive_delay_seconds)
    """
    now = time.time()
    cutoff = now - settings.AUTH_RATE_LIMIT_WINDOW

    with _lock:
        attempts = [t for t in _ip_attempts.get(ip, []) if t > cutoff]
        count = len(attempts)

    # If count exceeds threshold, calculate progressive delay (up to 3 seconds)
    if count >= settings.AUTH_MAX_ATTEMPTS:
        excess = count - settings.AUTH_MAX_ATTEMPTS
        delay = min(0.5 + (excess * 0.5), 3.0)
        return True, delay

    return False, 0.0


def apply_progressive_delay(ip: str):
    """
    Applies sleep delay if the IP has multiple consecutive attempts.
    """
    is_throttled, delay = check_ip_rate_limit(ip)
    if is_throttled and delay > 0:
        time.sleep(delay)


def is_account_locked(user: models.User) -> Tuple[bool, Optional[int]]:
    """
    Check if account is temporarily locked due to excessive failed attempts.
    Returns (is_locked, remaining_seconds).
    """
    if not user.locked_until:
        return False, None

    now = datetime.utcnow()
    if now < user.locked_until:
        remaining = int((user.locked_until - now).total_seconds())
        return True, max(remaining, 1)

    # Lock has expired; reset
    user.locked_until = None
    user.failed_login_attempts = 0
    return False, None


def record_failed_attempt(user: Optional[models.User], db) -> bool:
    """
    Increment failed login count for existing user and apply cooldown if threshold reached.
    Returns True if account has become locked.
    """
    if not user:
        return False

    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    became_locked = False

    if user.failed_login_attempts >= settings.AUTH_COOLDOWN_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(seconds=settings.AUTH_COOLDOWN_SECONDS)
        became_locked = True

    user.updated_at = datetime.utcnow()
    db.commit()
    return became_locked


def reset_failed_attempts(user: models.User, db):
    """
    Reset failed login attempts and clear lock state upon successful authentication.
    """
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    db.commit()


def timing_safe_dummy_verify(provided_password: str):
    """
    Perform a dummy bcrypt verification on nonexistent accounts so response times
    match authentic user password evaluations, mitigating timing attack user enumeration.
    """
    try:
        pw_bytes = provided_password.encode("utf-8")[:72]
        dummy_bytes = DUMMY_HASH.encode("utf-8")
        bcrypt.checkpw(pw_bytes, dummy_bytes)
    except Exception:
        pass
