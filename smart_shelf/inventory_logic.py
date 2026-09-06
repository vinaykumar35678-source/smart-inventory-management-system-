import os
import csv
from datetime import datetime
from database import Session, Product, Event, Alert
from anomaly_detection import detector

LOW_STOCK_NOTIFY = 5   # global floor that always triggers an alert
CSV_FILE_PATH    = os.path.join(os.path.dirname(__file__), "inventory.csv")


def _append_to_csv(timestamp: datetime, product_name: str, event_type: str, quantity: int, current_stock: int):
    """Write inventory transaction to inventory.csv"""
    file_exists = os.path.exists(CSV_FILE_PATH)
    try:
        with open(CSV_FILE_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Product", "Event_Type", "Quantity", "Current_Stock"])
            writer.writerow([timestamp.strftime("%Y-%m-%d %H:%M:%S"), product_name, event_type, quantity, current_stock])
    except Exception as exc:
        print(f"[inventory_logic] CSV log error: {exc}")


def process_addition(product_name: str, quantity: int, confidence: float,
                     socketio=None) -> dict:
    """
    1. Log addition event in SQLite & CSV
    2. Increment stock
    3. Broadcast via SocketIO
    Returns result dict.
    """
    db = Session()
    try:
        now = datetime.utcnow()
        event = Event(
            product_name=product_name,
            event_type="ADDITION",
            quantity_removed=-quantity,
            confidence=confidence,
            timestamp=now
        )
        db.add(event)

        product   = db.query(Product).filter(Product.name == product_name).first()
        new_stock = None

        if product:
            product.stock      += quantity
            product.updated_at = now
            new_stock          = product.stock
        else:
            product = Product(name=product_name, stock=quantity, threshold=5, price=0.0, category="General", created_at=now, updated_at=now)
            db.add(product)
            new_stock = quantity

        db.commit()
        _append_to_csv(now, product_name, "ADDITION", quantity, new_stock)

        result = {
            "type":       "addition",
            "product":    product_name,
            "quantity":   quantity,
            "confidence": round(confidence, 3),
            "timestamp":  now.isoformat(),
            "stock":      new_stock,
        }

        if socketio:
            socketio.emit("inventory_update", result)

        return result

    except Exception as exc:
        db.rollback()
        print(f"[inventory_logic] Addition error: {exc}")
        return {"type": "error", "product": product_name, "message": str(exc)}
    finally:
        db.close()


def process_removal(product_name: str, quantity: int, confidence: float,
                    socketio=None) -> dict:
    """
    1. Log removal event in SQLite & CSV
    2. Decrement stock
    3. Create alert if below threshold
    4. Broadcast via SocketIO (if provided)
    Returns result dict.
    """
    db = Session()
    try:
        now = datetime.utcnow()
        # ── Log event ────────────────────────────────────────
        event = Event(
            product_name=product_name,
            event_type="REMOVAL",
            quantity_removed=quantity,
            confidence=confidence,
            timestamp=now
        )
        db.add(event)

        # ── Update stock ──────────────────────────────────────
        product   = db.query(Product).filter(Product.name == product_name).first()
        new_stock = 0
        alert_msg = None

        if product:
            product.stock      = max(0, product.stock - quantity)
            product.updated_at = now
            new_stock          = product.stock

            # --- 1. Predictive Anomaly & Theft Detection ---
            last_event = db.query(Event).filter(Event.product_name == product_name, Event.event_type == "REMOVAL").order_by(Event.timestamp.desc()).first()
            time_since_last = (now - last_event.timestamp).total_seconds() if last_event else 3600.0
            
            is_theft = detector.is_anomalous(product_name, quantity, time_since_last)
            
            # Alert check
            trigger_at = min(product.threshold, LOW_STOCK_NOTIFY)
            
            if is_theft:
                alert_msg = f"🚨 SUSPECTED THEFT: Anomalous rapid removal of '{product_name}' (Qty: {quantity})!"
                alert = Alert(product_name=product_name, message=alert_msg, is_resolved=False, timestamp=now)
                db.add(alert)
            elif product.stock <= trigger_at:
                if product.stock <= 0:
                    alert_msg = f"OUT OF STOCK: '{product_name}' has 0 units left!"
                else:
                    alert_msg = (
                        f"Low stock: '{product_name}' has only {product.stock} "
                        f"unit(s) remaining (threshold: {product.threshold})."
                    )
                alert = Alert(
                    product_name=product_name,
                    message=alert_msg,
                    is_resolved=False,
                    timestamp=now
                )
                db.add(alert)

        db.commit()
        _append_to_csv(now, product_name, "REMOVAL", quantity, new_stock)

        result = {
            "type":       "removal",
            "product":    product_name,
            "quantity":   quantity,
            "confidence": round(confidence, 3),
            "timestamp":  now.isoformat(),
            "stock":      new_stock,
        }

        # ── Broadcast via SocketIO ────────────────────────────
        if socketio:
            socketio.emit("inventory_update", result)
            if alert_msg:
                socketio.emit("alert", {
                    "product":   product_name,
                    "stock":     new_stock,
                    "message":   alert_msg,
                    "timestamp": now.isoformat(),
                })

        return result

    except Exception as exc:
        db.rollback()
        print(f"[inventory_logic] Error: {exc}")
        return {"type": "error", "product": product_name, "message": str(exc)}
    finally:
        db.close()

