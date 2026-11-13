"""
app.py – Application factory for ResumeX.

Learning note:
  The "application factory" pattern (create_app function) is the recommended
  Flask architecture.  Instead of creating the Flask app as a module-level
  global, we create it inside a function.  This lets us:
    1. Create multiple instances with different configs (great for testing).
    2. Avoid circular imports between modules.
    3. Register blueprints (groups of routes) cleanly.
"""

import os
from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS

from config import config_map
from models.database import db, init_db


def create_app(env: str | None = None) -> Flask:
    """
    Create, configure and return the Flask application.

    Args:
        env: One of 'development', 'production', 'testing'.
             Defaults to the FLASK_ENV environment variable, or 'development'.
    """
    if env is None:
        env = os.environ.get("FLASK_ENV", "development")

    # ── Create Flask app ──────────────────────────────────────────────────────
    # static_folder / static_url_path: serve files from frontend/ at the root URL
    app = Flask(
        __name__,
        static_folder="frontend",
        static_url_path=""
    )

    # ── Load configuration ─────────────────────────────────────────────────────
    app.config.from_object(config_map.get(env, config_map["default"]))

    # Ensure upload and report directories exist on disk
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["REPORTS_FOLDER"]).mkdir(parents=True, exist_ok=True)

    # ── Extensions ────────────────────────────────────────────────────────────
    # CORS: allow the frontend (served from the same origin) to call the API
    CORS(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    # Database: bind SQLAlchemy to this app instance
    init_db(app)

    # ── Register route blueprints ─────────────────────────────────────────────
    # Each blueprint lives in backend/routes.py and groups related endpoints.
    # We import here (inside the factory) to prevent circular imports.
    from backend.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    # ── Frontend catch-all route ───────────────────────────────────────────────
    # Serve any .html file from the frontend/ directory by name.
    # This lets the browser request /dashboard.html and get the right page.
    @app.route("/")
    def index():
        return send_from_directory("frontend", "index.html")

    @app.route("/<path:filename>")
    def frontend_files(filename):
        return send_from_directory("frontend", filename)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        return {"status": "ok", "app": "ResumeX", "env": env}

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
# Running `python app.py` starts the development server.
# In production use a WSGI server like Gunicorn instead.
if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=flask_app.config.get("DEBUG", True)
    )

