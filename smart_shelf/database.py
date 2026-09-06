"""
database.py  — SQLAlchemy setup + all ORM models
"""
import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Boolean, Text, text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

_DB_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(_DB_DIR, 'inventory.db')}"

engine  = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base    = declarative_base()


# ── ORM Models ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String, unique=True, index=True, nullable=False)
    full_name       = Column(String, default="")
    email           = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role            = Column(String, default="user")   # "admin" | "user"
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String, unique=True, index=True, nullable=False)
    stock      = Column(Integer, default=0)
    threshold  = Column(Integer, default=5)
    price      = Column(Float, default=0.0)
    category   = Column(String, default="General")
    image_url  = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id               = Column(Integer, primary_key=True, index=True)
    product_name     = Column(String, index=True)
    event_type       = Column(String, default="REMOVAL")  # "ADDITION" or "REMOVAL"
    quantity_removed = Column(Integer, default=1)
    confidence       = Column(Float, default=1.0)
    timestamp        = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id           = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, index=True)
    message      = Column(Text)
    is_resolved  = Column(Boolean, default=False)
    timestamp    = Column(DateTime, default=datetime.utcnow)
    resolved_at  = Column(DateTime, nullable=True)


def init_db():
    """Create all tables and migrate columns if missing."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN event_type VARCHAR DEFAULT 'REMOVAL'"))
            print("[Database] Migrated 'events' table to include 'event_type' column.")
        except Exception:
            pass  # Column already exists
