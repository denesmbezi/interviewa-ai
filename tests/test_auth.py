from fastapi.testclient import TestClient

from app.main import app


def test_login_success():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@interviewa.ai", "password": "password123"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["message"] == "Logged in"


def test_login_failure():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@interviewa.ai", "password": "wrong"},
        )
        assert response.status_code == 401


def test_dashboard_requires_auth():
    with TestClient(app) as client:
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 401
