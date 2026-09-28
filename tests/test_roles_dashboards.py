from fastapi.testclient import TestClient
from app.main import app

def test_roles_and_dashboards():
    with TestClient(app) as client:
        # Candidate login & /me check
        res_cand = client.post("/api/auth/login", json={"email": "candidate@interviewa.ai", "password": "password123"})
        assert res_cand.status_code == 200
        me_cand = client.get("/api/auth/me")
        assert me_cand.status_code == 200
        assert me_cand.json()["role"] == "Candidate"

        # Candidate dashboard endpoint
        dash_cand = client.get("/api/candidate/dashboard")
        assert dash_cand.status_code == 200
        data_cand = dash_cand.json()
        assert "open_jobs" in data_cand
        assert "applications" in data_cand

        # Logout
        client.post("/api/auth/logout")

        # Hiring team login & /me check
        res_hiring = client.post("/api/auth/login", json={"email": "hiring@interviewa.ai", "password": "password123"})
        assert res_hiring.status_code == 200
        me_hiring = client.get("/api/auth/me")
        assert me_hiring.status_code == 200
        assert me_hiring.json()["role"] == "Hiring Team"

        # Hiring team applications endpoint
        emp_apps = client.get("/api/employer/applications")
        assert emp_apps.status_code == 200
