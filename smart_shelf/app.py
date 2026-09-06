"""
app.py  — Main Flask application
Smart Shelf Inventory Vision System — Pure Python
Covers all 5 project objectives:
  1. YOLO11 product detection
  2. Real-time inventory tracking
  3. Differential frame detection (product removal)
  4. User-friendly web dashboard
  5. Reduced human effort / automated alerts
"""
import os
import base64
import json
from datetime import datetime
from functools import wraps

import cv2
import numpy as np
import pandas as pd
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, send_file
)
from flask_socketio import SocketIO, emit
import bcrypt
from sqlalchemy import func

from database import Session, User, Product, Event, Alert
from detection import detect_from_frame, simulate_one_event, compare_frames, reset_frame_tracking
from inventory_logic import process_removal, process_addition

# ── App setup ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "smartshelf-secret-key-2024"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

class PwdContext:
    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

pwd_ctx = PwdContext()


# ── Auth helpers ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = Session()
        try:
            user = db.query(User).filter(User.username == username).first()
            if user and pwd_ctx.verify(password, user.hashed_password) and user.is_active:
                session["user"]      = user.username
                session["role"]      = user.role
                session["full_name"] = user.full_name or user.username
                flash(f"Welcome back, {session['full_name']}!", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "danger")
        finally:
            db.close()
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    db = Session()
    try:
        total_products   = db.query(Product).count()
        low_stock        = db.query(Product).filter(Product.stock <= Product.threshold).count()
        total_events     = db.query(Event).count()
        unresolved_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()

        recent_events = (
            db.query(Event)
            .order_by(Event.timestamp.desc())
            .limit(10)
            .all()
        )
        recent_alerts = (
            db.query(Alert)
            .filter(Alert.is_resolved == False)
            .order_by(Alert.timestamp.desc())
            .limit(5)
            .all()
        )
        low_stock_products = (
            db.query(Product)
            .filter(Product.stock <= Product.threshold)
            .order_by(Product.stock.asc())
            .all()
        )
        # Category distribution for chart
        category_data = (
            db.query(Product.category, func.count(Product.id))
            .group_by(Product.category)
            .all()
        )
        cat_labels = [r[0] for r in category_data]
        cat_counts = [r[1] for r in category_data]

        return render_template(
            "dashboard.html",
            total_products=total_products,
            low_stock=low_stock,
            total_events=total_events,
            unresolved_alerts=unresolved_alerts,
            recent_events=recent_events,
            recent_alerts=recent_alerts,
            low_stock_products=low_stock_products,
            cat_labels=json.dumps(cat_labels),
            cat_counts=json.dumps(cat_counts),
        )
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────
# INVENTORY
# ─────────────────────────────────────────────────────────────────────────

@app.route("/inventory")
@login_required
def inventory():
    db = Session()
    try:
        products = db.query(Product).order_by(Product.category, Product.name).all()
        return render_template("inventory.html", products=products)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────
# ALERTS
# ─────────────────────────────────────────────────────────────────────────

@app.route("/alerts")
@login_required
def alerts():
    db = Session()
    try:
        all_alerts = db.query(Alert).order_by(Alert.timestamp.desc()).all()
        return render_template("alerts.html", alerts=all_alerts)
    finally:
        db.close()


@app.route("/alerts/resolve/<int:alert_id>", methods=["POST"])
@login_required
def resolve_alert(alert_id):
    db = Session()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()
            db.commit()
            flash("Alert resolved.", "success")
    finally:
        db.close()
    return redirect(url_for("alerts"))


# ─────────────────────────────────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────────────────────────────────

@app.route("/events")
@login_required
def events():
    db = Session()
    try:
        all_events = db.query(Event).order_by(Event.timestamp.desc()).limit(200).all()
        return render_template("events.html", events=all_events)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────
# ADMIN — PRODUCTS
# ─────────────────────────────────────────────────────────────────────────

@app.route("/admin/products")
@admin_required
def admin_products():
    db = Session()
    try:
        products = db.query(Product).order_by(Product.category, Product.name).all()
        return render_template("admin_products.html", products=products)
    finally:
        db.close()


@app.route("/admin/products/add", methods=["POST"])
@admin_required
def add_product():
    db = Session()
    try:
        name      = request.form.get("name", "").strip()
        stock     = int(request.form.get("stock", 0))
        threshold = int(request.form.get("threshold", 5))
        price     = float(request.form.get("price", 0.0))
        category  = request.form.get("category", "General").strip()
        image_url = request.form.get("image_url", "").strip()

        existing = db.query(Product).filter(Product.name == name).first()
        if existing:
            flash("A product with that name already exists.", "danger")
        else:
            now = datetime.utcnow()
            p   = Product(name=name, stock=stock, threshold=threshold,
                          price=price, category=category, image_url=image_url,
                          created_at=now, updated_at=now)
            db.add(p)
            db.commit()
            flash(f"Product '{name}' added successfully.", "success")
    except ValueError:
        flash("Invalid number value entered.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_products"))


@app.route("/admin/products/edit/<int:product_id>", methods=["POST"])
@admin_required
def edit_product(product_id):
    db = Session()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            flash("Product not found.", "danger")
        else:
            product.stock      = int(request.form.get("stock", product.stock))
            product.threshold  = int(request.form.get("threshold", product.threshold))
            product.price      = float(request.form.get("price", product.price))
            product.category   = request.form.get("category", product.category).strip()
            product.updated_at = datetime.utcnow()
            db.commit()
            flash(f"Product '{product.name}' updated.", "success")
    except ValueError:
        flash("Invalid number value.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_products"))


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    db = Session()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            db.delete(product)
            db.commit()
            flash(f"Product '{product.name}' deleted.", "success")
        else:
            flash("Product not found.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_products"))


# ─────────────────────────────────────────────────────────────────────────
# ADMIN — USERS
# ─────────────────────────────────────────────────────────────────────────

@app.route("/admin/users")
@admin_required
def admin_users():
    db = Session()
    try:
        users = db.query(User).order_by(User.username).all()
        return render_template("admin_users.html", users=users)
    finally:
        db.close()


@app.route("/admin/users/add", methods=["POST"])
@admin_required
def add_user():
    db = Session()
    try:
        username  = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email", "").strip() or None
        password  = request.form.get("password", "")
        role      = request.form.get("role", "user")

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            flash("Username already exists.", "danger")
        else:
            u = User(
                username=username, full_name=full_name, email=email,
                hashed_password=pwd_ctx.hash(password),
                role=role, is_active=True, created_at=datetime.utcnow()
            )
            db.add(u)
            db.commit()
            flash(f"User '{username}' created.", "success")
    finally:
        db.close()
    return redirect(url_for("admin_users"))


@app.route("/admin/users/toggle/<int:user_id>", methods=["POST"])
@admin_required
def toggle_user(user_id):
    db = Session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.username != "admin":
            user.is_active = not user.is_active
            db.commit()
            status = "activated" if user.is_active else "deactivated"
            flash(f"User '{user.username}' {status}.", "success")
    finally:
        db.close()
    return redirect(url_for("admin_users"))


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    db = Session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.username != "admin":
            db.delete(user)
            db.commit()
            flash(f"User '{user.username}' deleted.", "success")
        else:
            flash("Cannot delete admin or user not found.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_users"))


# ─────────────────────────────────────────────────────────────────────────
# DETECTION — LIVE CAMERA FRAME  (Objective 1 & 3)
# ─────────────────────────────────────────────────────────────────────────

@app.route("/api/detect/reset", methods=["POST"])
@login_required
def api_detect_reset():
    """Reset tracked objects when starting or restarting live camera."""
    reset_frame_tracking()
    return jsonify({"status": "reset"})


@app.route("/api/detect/frame", methods=["POST"])
@login_required
def api_detect_frame():
    """
    Accept a base64 JPEG/PNG from the browser webcam.
    Run YOLO11 → diff frame comparison:
    1. Detect products in the frame for first time: mark addition of object.
      - If object remains in frame: do nothing.
      - If object is removed from frame: mark removal of object.
    """
    data = request.get_json(silent=True) or {}
    img_b64 = data.get("image", "")
    if not img_b64:
        return jsonify({"error": "No image provided", "detected": []}), 400

    # Strip data-URL prefix
    if "," in img_b64:
        img_b64 = img_b64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(img_b64)
        np_arr    = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"error": "Could not decode image", "detected": []}), 400
    except Exception as exc:
        return jsonify({"error": f"Decode error: {exc}", "detected": []}), 400

    items           = detect_from_frame(frame)
    results         = []
    persons_seen    = 0
    current_labels  = []

    for item_info in items:
        label    = item_info.get("label", "Unknown")
        conf     = round(float(item_info.get("confidence", 0.9)), 3)
        category = item_info.get("category", "item")
        ts       = datetime.utcnow().isoformat()

        if category == "person":
            persons_seen += 1
            payload = {"type": "person", "label": "Person",
                       "message": "Person detected near shelf",
                       "confidence": conf, "timestamp": ts}
            socketio.emit("person_detected", payload)
            results.append(payload)
            continue

        current_labels.append(label)

    # Differential frame comparison — detect items added or removed relative to previous frame
    added, removed = compare_frames(current_labels)

    # 1. Objects entering frame for the first time -> Addition
    for prod_name, qty in added.items():
        result = process_addition(prod_name, qty, 0.85, socketio)
        results.append(result)

    # 2. Objects leaving frame -> Removal
    for prod_name, qty in removed.items():
        result = process_removal(prod_name, qty, 0.85, socketio)
        results.append(result)

    # 3. Objects remaining in frame -> Do nothing (neither added nor removed)

    return jsonify({
        "detected": results,
        "persons_detected": persons_seen,
        "current_items": current_labels,
        "raw_detections": items
    })


# ─────────────────────────────────────────────────────────────────────────
# DETECTION — SIMULATE  (Objective 5 testing)
# ─────────────────────────────────────────────────────────────────────────

@app.route("/api/detect/simulate", methods=["POST"])
@login_required
def api_simulate():
    """Trigger a simulated removal event for demo purposes."""
    detected = simulate_one_event()
    results  = []
    for product_name, info in detected.items():
        qty  = info.get("quantity", 1)
        conf = info.get("confidence", 0.95)
        result = process_removal(product_name, qty, conf, socketio)
        results.append(result)
    return jsonify({"detected": results})


# ─────────────────────────────────────────────────────────────────────────
# LIVE DETECTION PAGE
# ─────────────────────────────────────────────────────────────────────────

@app.route("/live")
@login_required
def live_detection():
    return render_template("live_detection.html")


# ─────────────────────────────────────────────────────────────────────────
# EXPORT  (Objective 5 — reduce effort)
# ─────────────────────────────────────────────────────────────────────────

@app.route("/api/export/excel")
@login_required
def export_excel():
    db = Session()
    try:
        products = db.query(Product).all()
        data = [
            {
                "ID": p.id, "Name": p.name, "Category": p.category,
                "Stock": p.stock, "Threshold": p.threshold, "Price (Rs)": p.price,
                "Status": "Low Stock" if p.stock <= p.threshold else "OK",
                "Last Updated": p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else "",
            }
            for p in products
        ]
        df          = pd.DataFrame(data)
        export_path = os.path.join(os.path.dirname(__file__), "inventory_export.xlsx")
        with pd.ExcelWriter(export_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Inventory")
        return send_file(
            export_path,
            as_attachment=True,
            download_name="inventory_export.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────
# SOCKET.IO — Real-time events  (Objective 2)
# ─────────────────────────────────────────────────────────────────────────

@socketio.on("connect")
def handle_connect():
    emit("connected", {"message": "Real-time connection established"})


@socketio.on("ping_server")
def handle_ping():
    emit("pong_server", {"ts": datetime.utcnow().isoformat()})


# ─────────────────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from database import init_db as _init_db
    from seed import seed as _seed
    _init_db()
    _seed()
    print("=" * 60)
    print("  Smart Shelf Inventory Vision System")
    print("  URL : http://localhost:5000")
    print("  User: admin  /  Password: Admin@123")
    print("  User: staff  /  Password: Staff@123")
    print("=" * 60)
    socketio.run(app, debug=True, host="0.0.0.0", port=5000,
                 use_reloader=False, allow_unsafe_werkzeug=True)
