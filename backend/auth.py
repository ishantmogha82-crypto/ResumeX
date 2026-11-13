"""
backend/auth.py – Authentication and Session Management for ResumeX.

Provides:
- Secure password hashing and verification using Werkzeug (pbkdf2:sha256)
- Registration, login, logout, and session verification
- Login required decorator for route protection
"""

from functools import wraps
from flask import session, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, User


def register_user(name: str, email: str, password: str):
    """
    Register a new user account.
    Returns: (User, None) on success or (None, error_message) on failure.
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()

    if not name:
        return None, "Name is required."
    if not email or "@" not in email:
        return None, "A valid email address is required."
    if not password or len(password) < 6:
        return None, "Password must be at least 6 characters long."

    existing = User.query.filter_by(email=email).first()
    if existing:
        return None, "An account with this email address already exists."

    password_hash = generate_password_hash(password, method="scrypt")
    user = User(name=name, email=email, password_hash=password_hash)

    try:
        db.session.add(user)
        db.session.commit()
        return user, None
    except Exception as e:
        db.session.rollback()
        return None, f"Database error during registration: {str(e)}"


def authenticate_user(email: str, password: str):
    """
    Authenticate a user by email and password.
    Returns: (User, None) on success or (None, error_message) on failure.
    """
    email = (email or "").strip().lower()
    if not email or not password:
        return None, "Email and password are required."

    user = User.query.filter_by(email=email).first()
    if not user:
        return None, "Invalid email or password."

    if not check_password_hash(user.password_hash, password):
        return None, "Invalid email or password."

    return user, None


def login_user_session(user: User):
    """Store the authenticated user id in Flask session."""
    session.clear()
    session["user_id"] = user.id
    session.permanent = True


def logout_user_session():
    """Clear user session."""
    session.clear()


def get_current_user():
    """Retrieve the current logged-in User instance from session, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(f):
    """Decorator to protect routes requiring authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                "error": "Authentication required. Please sign in.",
                "code": "UNAUTHORIZED"
            }), 401
        return f(*args, **kwargs)
    return decorated_function
