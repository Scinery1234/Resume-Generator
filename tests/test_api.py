"""
Integration tests for the FastAPI application (main.py).
Uses TestClient from httpx/starlette – no real database calls for most tests
(the DB is SQLite in-memory or a temp file).
"""
import os
import json
import pytest
from pathlib import Path

# Use a temp SQLite DB to avoid touching the production DB
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_temp.db")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ── Health endpoints ─────────────────────────────────────────────────────────

class TestHealth:
    def test_root_returns_healthy(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_health_endpoint(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


# ── Auth endpoints ───────────────────────────────────────────────────────────

class TestAuth:
    _email = "testauth_unique_xyz@example.com"
    _password = "testpass123"
    _name = "Auth Test User"

    def test_signup_creates_user(self):
        resp = client.post("/api/auth/signup", json={
            "name": self._name,
            "email": self._email,
            "password": self._password,
        })
        # May already exist from a previous run – both 200 and 400 are acceptable
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "success"
            assert "token" in data
            assert "user_id" in data

    def test_signup_duplicate_email_returns_400(self):
        # Ensure the user exists first
        client.post("/api/auth/signup", json={
            "name": "Dup User",
            "email": "dup_test_xyz@example.com",
            "password": "password123",
        })
        resp = client.post("/api/auth/signup", json={
            "name": "Dup User 2",
            "email": "dup_test_xyz@example.com",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_login_with_valid_credentials(self):
        email = "login_test_xyz@example.com"
        client.post("/api/auth/signup", json={"name": "Login User", "email": email, "password": "pass1234"})
        resp = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "token" in data

    def test_login_with_wrong_password_returns_401(self):
        email = "wrongpass_xyz@example.com"
        client.post("/api/auth/signup", json={"name": "WP User", "email": email, "password": "correct"})
        resp = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self):
        resp = client.post("/api/auth/login", json={
            "email": "nobody_xyz_zz@example.com",
            "password": "pass",
        })
        assert resp.status_code == 401


# ── Preview endpoint ─────────────────────────────────────────────────────────

SAMPLE_CANDIDATE = {
    "name": "Test User",
    "contact": {
        "email": "test.user@example.com",
        "phone": "0400000000",
        "location": "Sydney, NSW",
    },
    "professional_summary": "Test candidate for automated testing purposes.",
    "key_skills": ["Testing", "Automation"],
    "technical_skills": ["Python", "pytest"],
    "experience": [
        {
            "title": "QA Engineer",
            "company": "Test Corp",
            "location": "Sydney, NSW",
            "dates": "Jan 2022 – Present",
            "description": "Automated test suites.",
            "bullets": ["Increased coverage by 30%"],
        }
    ],
    "education": [
        {
            "degree": "B.Sc. Computer Science",
            "field": "Testing",
            "institution": "Test University",
            "graduation_year": "2020",
        }
    ],
    "certifications": ["ISTQB Foundation"],
    "awards": [],
}


class TestPreviewResume:
    def test_preview_returns_200(self):
        resp = client.post("/api/preview-resume", json=SAMPLE_CANDIDATE)
        assert resp.status_code == 200

    def test_preview_returns_html_content_type(self):
        resp = client.post("/api/preview-resume", json=SAMPLE_CANDIDATE)
        assert "text/html" in resp.headers["content-type"]

    def test_preview_contains_candidate_name(self):
        resp = client.post("/api/preview-resume", json=SAMPLE_CANDIDATE)
        assert "TEST USER" in resp.text

    def test_preview_contains_contact_email(self):
        resp = client.post("/api/preview-resume", json=SAMPLE_CANDIDATE)
        assert "test.user@example.com" in resp.text

    def test_preview_contains_summary(self):
        resp = client.post("/api/preview-resume", json=SAMPLE_CANDIDATE)
        assert "automated testing purposes" in resp.text

    def test_preview_contains_experience(self):
        resp = client.post("/api/preview-resume", json=SAMPLE_CANDIDATE)
        assert "QA Engineer" in resp.text
        assert "Test Corp" in resp.text

    def test_preview_contains_education(self):
        resp = client.post("/api/preview-resume", json=SAMPLE_CANDIDATE)
        assert "B.Sc. Computer Science" in resp.text

    def test_preview_missing_required_field_returns_422(self):
        # Missing 'contact' field
        resp = client.post("/api/preview-resume", json={"name": "Incomplete"})
        assert resp.status_code == 422

    def test_preview_with_linkedin(self):
        candidate = dict(SAMPLE_CANDIDATE)
        candidate["contact"] = {**SAMPLE_CANDIDATE["contact"], "linkedin": "linkedin.com/in/testuser"}
        resp = client.post("/api/preview-resume", json=candidate)
        assert resp.status_code == 200
        assert "linkedin.com/in/testuser" in resp.text


# ── Generate resume endpoint ─────────────────────────────────────────────────

class TestGenerateResume:
    def test_generate_returns_success(self):
        resp = client.post("/api/generate-resume", json=SAMPLE_CANDIDATE)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "filename" in data["data"]

    def test_generate_creates_docx_file(self):
        resp = client.post("/api/generate-resume", json=SAMPLE_CANDIDATE)
        assert resp.status_code == 200
        filename = resp.json()["data"]["filename"]
        file_path = Path("./resumes") / filename
        assert file_path.exists()

    def test_generate_returns_download_url(self):
        resp = client.post("/api/generate-resume", json=SAMPLE_CANDIDATE)
        data = resp.json()["data"]
        assert "download_url" in data
        assert data["download_url"].startswith("/api/resumes/download-file/")

    def test_generate_missing_name_returns_422(self):
        bad = dict(SAMPLE_CANDIDATE)
        del bad["name"]
        resp = client.post("/api/generate-resume", json=bad)
        assert resp.status_code == 422

    def test_generate_missing_contact_returns_422(self):
        bad = dict(SAMPLE_CANDIDATE)
        del bad["contact"]
        resp = client.post("/api/generate-resume", json=bad)
        assert resp.status_code == 422


# ── Download endpoint ────────────────────────────────────────────────────────

class TestDownloadResume:
    def test_download_generated_file(self):
        # First generate a file
        gen_resp = client.post("/api/generate-resume", json=SAMPLE_CANDIDATE)
        assert gen_resp.status_code == 200
        filename = gen_resp.json()["data"]["filename"]

        dl_resp = client.get(f"/api/resumes/download-file/{filename}")
        assert dl_resp.status_code == 200
        assert "application/vnd.openxmlformats" in dl_resp.headers["content-type"]

    def test_download_nonexistent_file_returns_404(self):
        resp = client.get("/api/resumes/download-file/does_not_exist_xyz.docx")
        assert resp.status_code == 404


# ── Templates endpoint ───────────────────────────────────────────────────────

class TestTemplates:
    def test_get_templates_returns_list(self):
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert isinstance(data["templates"], list)
        assert len(data["templates"]) > 0

    def test_templates_have_required_fields(self):
        resp = client.get("/api/templates")
        for tpl in resp.json()["templates"]:
            assert "id" in tpl
            assert "name" in tpl
            assert "description" in tpl


# ── Resumes list endpoint ────────────────────────────────────────────────────

class TestResumesList:
    def test_get_resumes_for_unknown_user_returns_empty(self):
        resp = client.get("/api/resumes?user_id=99999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["resumes"] == []
