"""
config.py – Central configuration for ResumeX.

We define three Config classes so the application can run in different
modes without changing any code — just set the FLASK_ENV environment variable.

Learning note:
  Using a class-based config is a Flask best practice.  It keeps all settings
  in one place and makes it trivial to swap databases (SQLite → PostgreSQL)
  later by overriding a single string.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load values from the .env file (if present) into os.environ
load_dotenv()

# Absolute path of the project root (the folder that contains this file)
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration shared by all environments."""

    # ── Flask core ─────────────────────────────────────────────────────────────
    # SECRET_KEY is used to sign session cookies.  NEVER commit a real key.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-before-deploy")

    # ── Database ───────────────────────────────────────────────────────────────
    # SQLite for development; swap this URL for PostgreSQL in production:
    #   postgresql://user:password@host:5432/resumex
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'resumex.db'}"
    )
    # Disable modification tracking – saves memory and we don't need it
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ── File uploads ───────────────────────────────────────────────────────────
    UPLOAD_FOLDER: Path = BASE_DIR / "uploads"
    REPORTS_FOLDER: Path = BASE_DIR / "reports"
    ALLOWED_EXTENSIONS: set = {"pdf", "docx"}
    MAX_CONTENT_LENGTH: int = 5 * 1024 * 1024   # 5 MB hard limit enforced by Flask

    # ── Session ────────────────────────────────────────────────────────────────
    SESSION_TYPE: str = "filesystem"             # store sessions on disk, not in cookie
    SESSION_COOKIE_HTTPONLY: bool = True         # JS cannot read the cookie
    SESSION_COOKIE_SAMESITE: str = "Lax"        # CSRF mitigation

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list = ["http://localhost:5000", "http://127.0.0.1:5000"]


class DevelopmentConfig(Config):
    """Extra settings active during local development."""

    DEBUG: bool = True
    # In development we allow the session cookie over plain HTTP
    SESSION_COOKIE_SECURE: bool = False


class ProductionConfig(Config):
    """Settings for a deployed server."""

    DEBUG: bool = False
    # Cookies are only sent over HTTPS in production
    SESSION_COOKIE_SECURE: bool = True
    # In production, DATABASE_URL must be set in the environment
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", "")


class TestingConfig(Config):
    """Settings used by the automated test suite."""

    TESTING: bool = True
    # Use an in-memory SQLite database so tests never touch the real DB
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    WTF_CSRF_ENABLED: bool = False


# Map environment name → config class.
# Usage in app.py:  app.config.from_object(config_map[env])
config_map: dict = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
    "default":     DevelopmentConfig,
}

