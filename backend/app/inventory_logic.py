from collections import Counter
from datetime import datetime
from sqlalchemy.orm import Session
from . import models
from .websocket import manager
from .sms_alert import send_low_stock_sms, reset_alert
import asyncio

LOW_STOCK_NOTIFY = 5   # SMS + toast fires when stock drops below this number

from collections import Counter, deque
import statistics

previous_counts: dict = {}
count_history: dict = {}
stable_confirmed_counts: dict = {}


def compare_counts(current_items: list, confirmation_frames: int = 5) -> tuple:
    """
    Temporally Stabilized Counting Algorithm
    ----------------------------------------
    A count change must persist stably across multiple consecutive frames to be confirmed,
    preventing momentary YOLO detection drops or occlusion dips from triggering false removals.
    """
    global previous_counts, count_history, stable_confirmed_counts
    current_counts = Counter(current_items)
    removed = {}
    added = {}

    all_products = set(list(current_counts.keys()) + list(previous_counts.keys()) + list(count_history.keys()))
    
    for prod in all_products:
        if prod not in count_history:
            count_history[prod] = deque(maxlen=confirmation_frames)
        count_history[prod].append(current_counts.get(prod, 0))

        # Only evaluate after establishing stability window
        if len(count_history[prod]) >= confirmation_frames:
            stable_val = int(statistics.median(list(count_history[prod])))
            prev_stable = stable_confirmed_counts.get(prod, stable_val)

            if stable_val < prev_stable:
                removed[prod] = prev_stable - stable_val
                stable_confirmed_counts[prod] = stable_val
            elif stable_val > prev_stable:
                added[prod] = stable_val - prev_stable
                stable_confirmed_counts[prod] = stable_val
        else:
            stable_confirmed_counts[prod] = current_counts.get(prod, 0)

    previous_counts = dict(current_counts)
    return removed, added


def _broadcast_safe(payload: dict):
    """Broadcast a WebSocket message safely from a sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop and loop.is_running():
            asyncio.ensure_future(manager.broadcast(payload))
    except Exception:
        pass


def process_removal(product_name: str, quantity: int, confidence: float, db: Session):
    """
    Handle a detected removal:
    1. Log an Event
    2. Decrement product stock
    3. Create an Alert if stock falls below threshold or below LOW_STOCK_NOTIFY
    4. Broadcast via WebSocket (removal + optional alert)
    Returns the ws_payload dict for the API response.
    """
    # ── Log event ────────────────────────────────────────
    event = models.Event(
        product_name=product_name,
        quantity_removed=quantity,
        confidence=confidence,
        timestamp=datetime.utcnow()
    )
    db.add(event)

    # ── Decrement stock ───────────────────────────────────
    product = db.query(models.Product).filter(
        models.Product.name == product_name
    ).first()

    alert_data = None
    new_stock  = None

    if product:
        product.stock     = max(0, product.stock - quantity)
        product.updated_at = datetime.utcnow()
        new_stock          = product.stock

        # Alert if below per-product threshold OR globally below LOW_STOCK_NOTIFY
        trigger_threshold = min(product.threshold, LOW_STOCK_NOTIFY)
        if product.stock <= trigger_threshold:
            if product.stock <= 0:
                msg = f"🚨 OUT OF STOCK: '{product_name}' has no units left!"
            else:
                msg = (
                    f"⚠️ Low stock: '{product_name}' only has {product.stock} unit"
                    f"{'s' if product.stock != 1 else ''} remaining "
                    f"(threshold: {product.threshold})."
                )
            alert = models.Alert(
                product_name=product_name,
                message=msg,
                is_resolved=False,
                timestamp=datetime.utcnow()
            )
            db.add(alert)
            alert_data = {
                "type":    "alert",
                "product": product_name,
                "stock":   product.stock,
                "threshold": product.threshold,
                "message": msg,
            }

    db.commit()

    # ── Email notification state machine evaluation ──────
    if product:
        try:
            from .notifications.email_service import email_service
            email_service.evaluate_and_notify(product, db_session=db)
        except Exception:
            pass  # Never disrupt inventory transaction on notification failure

    # ── SMS alert if stock critically low ─────────────────
    if new_stock is not None and new_stock < LOW_STOCK_NOTIFY:
        try:
            send_low_stock_sms(product_name, new_stock)
        except Exception:
            pass  # Never crash on SMS failure

    # ── Broadcast removal ────────────────────────────────
    ws_payload = {
        "type":       "removal",
        "product":    product_name,
        "quantity":   quantity,
        "confidence": round(confidence, 3),
        "timestamp":  datetime.utcnow().isoformat(),
        "stock":      new_stock,
    }
    _broadcast_safe(ws_payload)

    # ── Broadcast alert if triggered ─────────────────────
    if alert_data:
        _broadcast_safe(alert_data)

    return ws_payload


def process_addition(product_name: str, quantity: int, confidence: float, db: Session):
    """
    Handle a detected addition (restocking):
    1. Log an Event (addition)
    2. Increment product stock
    3. Broadcast via WebSocket
    """
    # ── Log event (using negative quantity to denote addition, or just a separate log)
    # Since our Event schema uses quantity_removed, we will use a negative value 
    # to represent additions, or we can use the message field.
    event = models.Event(
        product_name=product_name,
        quantity_removed=-quantity,  # Negative means added
        confidence=confidence,
        timestamp=datetime.utcnow()
    )
    db.add(event)

    # ── Increment stock ───────────────────────────────────
    product = db.query(models.Product).filter(
        models.Product.name == product_name
    ).first()

    new_stock = None
    if product:
        product.stock += quantity
        product.updated_at = datetime.utcnow()
        new_stock = product.stock

        # If an alert existed for this product and stock is now okay, resolve it.
        if product.stock > product.threshold:
            open_alerts = db.query(models.Alert).filter(
                models.Alert.product_name == product_name,
                models.Alert.is_resolved == False
            ).all()
            for a in open_alerts:
                a.is_resolved = True
                a.resolved_at = datetime.utcnow()
            # Reset SMS alert tracker so future drops can re-trigger
            try:
                reset_alert(product_name)
            except Exception:
                pass

    db.commit()

    # ── Reset / evaluate notification state on restock ────
    if product:
        try:
            from .notifications.email_service import email_service
            email_service.evaluate_and_notify(product, db_session=db)
        except Exception:
            pass

    # ── Broadcast addition ────────────────────────────────
    ws_payload = {
        "type":       "addition",
        "product":    product_name,
        "quantity":   quantity,
        "confidence": round(confidence, 3),
        "timestamp":  datetime.utcnow().isoformat(),
        "stock":      new_stock,
    }
    _broadcast_safe(ws_payload)

    return ws_payload