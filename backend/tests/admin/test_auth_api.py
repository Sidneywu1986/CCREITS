"""
TDD: Auth API integration tests
Run: JWT_SECRET=test pytest tests/admin/test_auth_api.py -v
"""
import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "testadmin")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.app import app


@pytest.fixture
def client():
    """Fresh TestClient for each test (no cookie carry-over)."""
    # Clear in-memory rate-limit state between tests
    from admin.routes import auth
    auth._login_attempts.clear()
    auth._register_attempts.clear()
    return TestClient(app)


class TestRegister:
    def test_register_new_user(self, client):
        import uuid
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        res = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": "TestPass123!"
        })
        assert res.status_code in (200, 201)
        data = res.json()
        assert data["code"] == 201
        assert "id" in data.get("data", {})

    def test_register_duplicate_username(self, client):
        res = client.post("/api/v1/auth/register", json={
            "username": "admin",
            "email": "admin2@test.com",
            "password": "TestPass123!"
        })
        assert res.status_code in [200, 409]
        data = res.json()
        assert data["code"] in [201, 409]


class TestLogin:
    def test_login_admin(self, client):
        res = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        assert "access_token" in data.get("data", {})
        assert "refresh_token" in res.cookies

    def test_login_wrong_password(self, client):
        res = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 401


class TestMe:
    def test_me_without_token(self, client):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 401

    def test_me_with_valid_token(self, client):
        login_res = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = login_res.json()["data"]["access_token"]
        res = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        assert data["data"]["username"] == "admin"


class TestRefresh:
    def test_refresh_with_cookie(self, client):
        login_res = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        cookies = login_res.cookies
        res = client.post("/api/v1/auth/refresh", cookies=cookies)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        assert "access_token" in data.get("data", {})

    def test_refresh_without_cookie(self, client):
        res = client.post("/api/v1/auth/refresh")
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 401


class TestLogout:
    def test_logout(self, client):
        login_res = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        cookies = login_res.cookies
        res = client.post("/api/v1/auth/logout", cookies=cookies)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200


class TestChangePassword:
    def test_without_auth(self, client):
        res = client.post("/api/v1/auth/change-password", json={
            "old_password": "admin123",
            "new_password": "NewPass123!"
        })
        assert res.status_code == 401

    def test_wrong_old_password(self, client):
        login_res = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = login_res.json()["data"]["access_token"]
        res = client.post("/api/v1/auth/change-password", json={
            "old_password": "wrongpass",
            "new_password": "NewPass123!"
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
