"""
tests/test_auth.py – Unit and Integration Tests for ResumeX Authentication.
"""

import pytest
from app import create_app
from models.database import db, User


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_user_registration_success(client):
    res = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepassword123"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["user"]["email"] == "jane@example.com"
    assert data["user"]["name"] == "Jane Doe"
    assert "password_hash" not in data["user"]


def test_user_registration_duplicate_email(client):
    client.post("/api/auth/register", json={
        "name": "User 1",
        "email": "duplicate@example.com",
        "password": "password123"
    })
    res = client.post("/api/auth/register", json={
        "name": "User 2",
        "email": "duplicate@example.com",
        "password": "password456"
    })
    assert res.status_code == 400
    assert "already exists" in res.get_json()["error"]


def test_user_registration_short_password(client):
    res = client.post("/api/auth/register", json={
        "name": "User",
        "email": "user@example.com",
        "password": "123"
    })
    assert res.status_code == 400
    assert "at least 6 characters" in res.get_json()["error"]


def test_user_login_and_me(client):
    # Register
    client.post("/api/auth/register", json={
        "name": "Alex Smith",
        "email": "alex@example.com",
        "password": "mypassword"
    })
    # Logout first
    client.post("/api/auth/logout")

    # Verify unauthenticated me
    res_unauth = client.get("/api/auth/me")
    assert res_unauth.get_json()["user"] is None

    # Login
    res_login = client.post("/api/auth/login", json={
        "email": "alex@example.com",
        "password": "mypassword"
    })
    assert res_login.status_code == 200

    # Verify authenticated me
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 200
    assert res_me.get_json()["user"]["email"] == "alex@example.com"


def test_login_invalid_credentials(client):
    res = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "badpassword"
    })
    assert res.status_code == 401


def test_protected_route_requires_auth(client):
    res = client.get("/api/resumes")
    assert res.status_code == 401
    assert "Authentication required" in res.get_json()["error"]
