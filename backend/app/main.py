import os
import sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, SessionLocal
from .routes import router
from .websocket import manager
from .config import settings
from . import models
from .auth import hash_password
from datetime import datetime


def _seed_database():
    """Seed admin, a default user, and sample products on first run."""
    db = SessionLocal()
    try:
        # Seed users
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin_user:
            admin_user = models.User(
                username="admin",
                full_name="Administrator",
                email="admin@smartshelf.com",
                hashed_password=hash_password("Admin@123"),
                role="admin",
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(admin_user)

        user1_user = db.query(models.User).filter(models.User.username == "user1").first()
        if not user1_user:
            user1_user = models.User(
                username="user1",
                full_name="Store Staff",
                email="user1@smartshelf.com",
                hashed_password=hash_password("User@123"),
                role="user",
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(user1_user)
        db.commit()

        # Remove Beverages and Bakery categories if they exist
        removed_cats = db.query(models.Product).filter(
            models.Product.category.in_(["Beverages", "Bakery"])
        ).all()
        if removed_cats:
            for p in removed_cats:
                db.delete(p)
            db.commit()
            print(f"[Startup] Removed {len(removed_cats)} Beverages/Bakery products.")

        # Seed products (Fruits, Vegetables, Dairy, Electronics, Stationery only)
        if db.query(models.Product).count() == 0:
            sample_products = [
                # Fruits
                models.Product(name="Apple",        stock=45, threshold=10, price=2.50,   category="Fruits",      image_url="🍎"),
                models.Product(name="Banana",       stock=30, threshold=8,  price=1.20,   category="Fruits",      image_url="🍌"),
                models.Product(name="Orange",       stock=25, threshold=8,  price=4.00,   category="Fruits",      image_url="🍊"),
                # Vegetables
                models.Product(name="Carrot",       stock=18, threshold=6,  price=3.00,   category="Vegetables",  image_url="🥕"),
                # Dairy
                models.Product(name="Milk (1L)",    stock=8,  threshold=10, price=55.00,  category="Dairy",       image_url="🥛"),
                models.Product(name="Eggs (12)",    stock=6,  threshold=5,  price=80.00,  category="Dairy",       image_url="🥚"),
                # Electronics
                models.Product(name="Mobile Phone", stock=15, threshold=5,  price=8999.00, category="Electronics", image_url="📱"),
                models.Product(name="Calculator",   stock=10, threshold=3,  price=499.00,  category="Electronics", image_url="🖩"),
                # Stationery
                models.Product(name="Book",         stock=40, threshold=10, price=299.00,  category="Stationery",  image_url="📖"),
                models.Product(name="Pen",          stock=80, threshold=20, price=25.00,   category="Stationery",  image_url="🖊️"),
                models.Product(name="Paper Ream",   stock=20, threshold=5,  price=350.00,  category="Stationery",  image_url="📄"),
            ]
            for p in sample_products:
                p.created_at = datetime.utcnow()
                p.updated_at = datetime.utcnow()
                db.add(p)
        # Seed Shelves if none exist
        if db.query(models.Shelf).count() == 0:
            default_shelves = [
                models.Shelf(
                    name="Shelf 1 - Fresh Produce", category="Fruits", camera_id=1,
                    roi_x1=0.05, roi_y1=0.15, roi_x2=0.48, roi_y2=0.50,
                    capacity=30, current_count=20, status="NORMAL", created_at=datetime.utcnow()
                ),
                models.Shelf(
                    name="Shelf 2 - Dairy & Essentials", category="Dairy", camera_id=1,
                    roi_x1=0.52, roi_y1=0.15, roi_x2=0.95, roi_y2=0.50,
                    capacity=25, current_count=14, status="NORMAL", created_at=datetime.utcnow()
                ),
                models.Shelf(
                    name="Shelf 3 - Electronics", category="Electronics", camera_id=1,
                    roi_x1=0.05, roi_y1=0.55, roi_x2=0.48, roi_y2=0.90,
                    capacity=20, current_count=10, status="NORMAL", created_at=datetime.utcnow()
                ),
                models.Shelf(
                    name="Shelf 4 - Stationery", category="Stationery", camera_id=1,
                    roi_x1=0.52, roi_y1=0.55, roi_x2=0.95, roi_y2=0.90,
                    capacity=40, current_count=25, status="NORMAL", created_at=datetime.utcnow()
                ),
            ]
            for s in default_shelves:
                db.add(s)
            db.commit()
            print(f"[Startup] Seeded {len(default_shelves)} default virtual shelves.")

        # Seed Cameras if none exist
        if db.query(models.Camera).count() == 0:
            default_cams = [
                models.Camera(
                    name="Camera 1 - Overhead Shelf View", location="Aisle 1",
                    source="0", camera_type="webcam", status="ACTIVE", created_at=datetime.utcnow()
                ),
                models.Camera(
                    name="Camera 2 - Demo AI Scenario Cam", location="Testing Lab",
                    source="demo", camera_type="demo", status="ACTIVE", created_at=datetime.utcnow()
                ),
            ]
            for c in default_cams:
                db.add(c)
            db.commit()
            print(f"[Startup] Seeded {len(default_cams)} cameras.")

        # Update product shelf assignments if unassigned
        s1 = db.query(models.Shelf).filter(models.Shelf.name == "Shelf 1 - Fresh Produce").first()
        s2 = db.query(models.Shelf).filter(models.Shelf.name == "Shelf 2 - Dairy & Essentials").first()
        s3 = db.query(models.Shelf).filter(models.Shelf.name == "Shelf 3 - Electronics").first()
        s4 = db.query(models.Shelf).filter(models.Shelf.name == "Shelf 4 - Stationery").first()

        for p in db.query(models.Product).all():
            if not p.shelf_id:
                if p.category in ("Fruits", "Vegetables") and s1:
                    p.shelf_id = s1.id
                elif p.category == "Dairy" and s2:
                    p.shelf_id = s2.id
                elif p.category == "Electronics" and s3:
                    p.shelf_id = s3.id
                elif p.category == "Stationery" and s4:
                    p.shelf_id = s4.id
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    _seed_database()
    try:
        import asyncio
        from .ai.events.event_engine import set_main_loop
        set_main_loop(asyncio.get_running_loop())
    except Exception as e:
        print(f"[Startup] Note setting main loop: {e}")
    try:
        from ml.scripts.model_manager import model_manager
        from app.ai.detection.detector import detector
        active = model_manager.get_active_model_info()
        if active and active.get("is_custom") and os.path.exists(active.get("model_path", "")):
            detector.switch_model(active["model_path"], active.get("classes"))
            print(f"[Startup] Restored active custom model: {active.get('model_name')}")
    except Exception as e:
        print(f"[Startup] Active model check note: {e}")
    yield
    # Shutdown (nothing to clean up)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Smart camera-based inventory tracking for small grocery shops",
    lifespan=lifespan,
)

# ── Security Headers Middleware ───────────────────────────────────────────────
from .security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handler (Safe against Information Disclosure) ────────────
from fastapi.responses import JSONResponse
from fastapi.requests import Request
import traceback
import re

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log detailed internal stack trace to server console/logs only
    print(f"[Unhandled Server Error on {request.method} {request.url.path}]: {exc}")
    traceback.print_exc()

    # Safely evaluate origin against trusted list rather than reflecting wildcard with credentials
    origin = request.headers.get("origin")
    headers = {}
    if origin and (origin in settings.ALLOWED_ORIGINS or re.match(r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$", origin)):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"

    # Sanitized response: never return raw python traceback or internal service details to client
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact the administrator."},
        headers=headers,
    )

# ── API Routes ────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api")


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.disconnect(websocket)