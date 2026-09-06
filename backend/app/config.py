import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Settings:
    APP_NAME: str = os.environ.get("APP_NAME", "Smart Inventory Vision")
    APP_VERSION: str = os.environ.get("APP_VERSION", "1.0.0")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./inventory.db")
    YOLO_MODEL: str = os.environ.get("YOLO_MODEL", "yolo11n.pt")
    CONFIDENCE_THRESHOLD: float = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.5"))
    
    # Environment & Deployment
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")
    
    # Authentication & JWT
    AUTH_SECRET_KEY: str = os.environ.get("AUTH_SECRET_KEY", "smartshelf-super-secret-key-2024-inventory-vision")
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REMEMBER_ME_EXPIRE_DAYS: int = int(os.environ.get("REMEMBER_ME_EXPIRE_DAYS", "14"))
    
    # Rate Limiting & Brute Force Defense
    AUTH_RATE_LIMIT_WINDOW: int = int(os.environ.get("AUTH_RATE_LIMIT_WINDOW", "300"))
    AUTH_MAX_ATTEMPTS: int = int(os.environ.get("AUTH_MAX_ATTEMPTS", "5"))
    AUTH_COOLDOWN_ATTEMPTS: int = int(os.environ.get("AUTH_COOLDOWN_ATTEMPTS", "10"))
    AUTH_COOLDOWN_SECONDS: int = int(os.environ.get("AUTH_COOLDOWN_SECONDS", "900"))
    
    # Cookie Security (set to true in production over HTTPS)
    COOKIE_SECURE: bool = os.environ.get("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
    
    # CORS
    _raw_origins = os.environ.get("ALLOWED_ORIGINS")
    if _raw_origins:
        ALLOWED_ORIGINS: list = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    else:
        ALLOWED_ORIGINS: list = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]

    # Email / Gmail SMTP Settings
    GMAIL_ENABLED: bool = os.environ.get("GMAIL_ENABLED", "true").lower() in ("true", "1", "yes")
    GMAIL_USERNAME: str = os.environ.get("GMAIL_USERNAME", "")
    GMAIL_APP_PASSWORD: str = os.environ.get("GMAIL_APP_PASSWORD", "")
    GMAIL_FROM: str = os.environ.get("GMAIL_FROM", "") or os.environ.get("GMAIL_USERNAME", "")
    GMAIL_FROM_NAME: str = os.environ.get("GMAIL_FROM_NAME", "SmartShelf AI Alerts")
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USE_TLS: bool = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    SMTP_TIMEOUT: int = int(os.environ.get("SMTP_TIMEOUT", "10"))

settings = Settings()

