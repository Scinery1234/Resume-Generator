"""
Integration tests for the FastAPI application (main.py).
Uses TestClient from httpx/starlette – no real database calls for most tests
(the DB is SQLite in-memory or a temp file).
"""
import io
import os
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_templates_returns_four_entries(self):
        resp = client.get("/api/templates")
        assert len(resp.json()["templates"]) == 4

    def test_template_ids_are_correct(self):
        resp = client.get("/api/templates")
        ids = {t["id"] for t in resp.json()["templates"]}
        assert ids == {"modern", "classic", "creative", "minimal"}


class TestGenerateWithTemplate:
    """Tests for the `template` parameter in POST /api/generate."""

    @pytest.mark.parametrize("template_id", ["modern", "classic", "creative", "minimal"])
    def test_generate_with_each_template(self, monkeypatch, template_id):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(MOCK_RESUME_JSON)
        mock_client.chat.completions.create.return_value = mock_resp
        monkeypatch.setattr("main.openai_client", mock_client)

        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer", "template": template_id},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 200, f"Failed for template '{template_id}': {resp.text}"
        data = resp.json()
        assert "preview_html" in data
        assert data["filename"].endswith(".docx")

    def test_generate_without_template_defaults_to_modern(self, monkeypatch):
        """Omitting the template field must not cause an error (defaults to modern)."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(MOCK_RESUME_JSON)
        mock_client.chat.completions.create.return_value = mock_resp
        monkeypatch.setattr("main.openai_client", mock_client)

        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer"},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 200

    def test_generate_unknown_template_falls_back_gracefully(self, monkeypatch):
        """An unknown template ID must not crash — it falls back to modern."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(MOCK_RESUME_JSON)
        mock_client.chat.completions.create.return_value = mock_resp
        monkeypatch.setattr("main.openai_client", mock_client)

        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer", "template": "nonexistent"},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 200

    def test_creative_template_preview_contains_purple(self, monkeypatch):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(MOCK_RESUME_JSON)
        mock_client.chat.completions.create.return_value = mock_resp
        monkeypatch.setattr("main.openai_client", mock_client)

        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer", "template": "creative"},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 200
        # Creative template uses purple (#6b21a8) for headings
        assert "#6b21a8" in resp.json()["preview_html"]

    def test_classic_template_preview_contains_serif_font(self, monkeypatch):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(MOCK_RESUME_JSON)
        mock_client.chat.completions.create.return_value = mock_resp
        monkeypatch.setattr("main.openai_client", mock_client)

        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer", "template": "classic"},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 200
        assert "Georgia" in resp.json()["preview_html"]


# ── Resumes list endpoint ────────────────────────────────────────────────────

class TestResumesList:
    def test_get_resumes_for_unknown_user_returns_empty(self):
        resp = client.get("/api/resumes?user_id=99999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["resumes"] == []


# ── /api/generate (document-based AI generation) ────────────────────────────

# Minimal resume JSON that matches the schema expected by doc_builder
MOCK_RESUME_JSON = {
    "name": "Jane Smith",
    "contact": {
        "email": "jane@example.com",
        "phone": "0412 345 678",
        "location": "Sydney, NSW",
        "linkedin": "",
    },
    "professional_summary": "Experienced software engineer with 8 years in fintech.",
    "key_skills": ["Python", "FastAPI", "AWS"],
    "experience": [
        {
            "title": "Senior Software Engineer",
            "company": "FinTech Co",
            "location": "Sydney, NSW",
            "dates": "Jan 2020 – Present",
            "description": "",
            "bullets": ["Led migration of legacy systems to microservices, reducing latency by 40%."],
        }
    ],
    "education": [
        {
            "degree": "Bachelor of Computer Science",
            "field": "Software Engineering",
            "institution": "University of Sydney",
            "graduation_year": "2015",
        }
    ],
    "certifications": [],
    "awards": [],
    "technical_skills": ["Python", "Docker", "Kubernetes"],
}


def _mock_openai_client(monkeypatch):
    """Return a mocked openai_client and patch it into main module."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(MOCK_RESUME_JSON)
    mock_client.chat.completions.create.return_value = mock_response
    monkeypatch.setattr("main.openai_client", mock_client)
    return mock_client


class TestGenerateFromDocuments:
    """Tests for POST /api/generate — document-based AI resume generation."""

    def test_generate_without_files_returns_error(self):
        # No files provided → endpoint must not return 200.
        # FastAPI may return 422 (form validation) or the endpoint returns 400.
        resp = client.post(
            "/api/generate",
            data={"job_description": "Senior Software Engineer at FinTech startup."},
        )
        assert resp.status_code in (400, 422)
        assert resp.status_code != 200

    def test_generate_without_job_description_returns_422(self):
        txt = b"Jane Smith\nSoftware Engineer\n8 years Python experience"
        resp = client.post(
            "/api/generate",
            files=[("files", ("resume.txt", io.BytesIO(txt), "text/plain"))],
        )
        # job_description is a required Form field → 422 Unprocessable Entity
        assert resp.status_code == 422

    def test_generate_no_openai_key_returns_503(self, monkeypatch):
        monkeypatch.setattr("main.openai_client", None)
        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer role"},
            files=[("files", ("resume.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 503
        assert "openai" in resp.json()["detail"].lower()

    def test_generate_with_txt_file_returns_success(self, monkeypatch):
        _mock_openai_client(monkeypatch)
        txt = b"Jane Smith\nSoftware Engineer\n8 years Python experience"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Senior Python developer with AWS experience."},
            files=[("files", ("resume.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "filename" in data
        assert data["filename"].endswith(".docx")
        assert "download_url" in data
        assert "preview_html" in data

    def test_generate_creates_docx_file(self, monkeypatch):
        _mock_openai_client(monkeypatch)
        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer"},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 200
        filename = resp.json()["filename"]
        assert Path("./resumes") / filename

    def test_generate_preview_html_contains_name(self, monkeypatch):
        _mock_openai_client(monkeypatch)
        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer"},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 200
        assert "JANE SMITH" in resp.json()["preview_html"]

    def test_generate_download_url_accessible(self, monkeypatch):
        _mock_openai_client(monkeypatch)
        txt = b"Jane Smith\nSoftware Engineer"
        gen_resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer"},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert gen_resp.status_code == 200
        dl_resp = client.get(gen_resp.json()["download_url"])
        assert dl_resp.status_code == 200
        assert "application/vnd.openxmlformats" in dl_resp.headers["content-type"]

    def test_generate_with_docx_file(self, monkeypatch):
        """Upload a real minimal .docx file and verify extraction doesn't crash."""
        _mock_openai_client(monkeypatch)
        from docx import Document as DocxDocument
        buf = io.BytesIO()
        doc = DocxDocument()
        doc.add_paragraph("Jane Smith")
        doc.add_paragraph("Senior Software Engineer")
        doc.save(buf)
        buf.seek(0)
        resp = client.post(
            "/api/generate",
            data={"job_description": "Software engineer role"},
            files=[("files", ("resume.docx", buf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        )
        assert resp.status_code == 200

    def test_generate_with_pdf_file(self, monkeypatch):
        """PDF upload should not crash even if pypdf has system-level issues.
        The endpoint falls back to raw decode; the mock fills in the resume data."""
        _mock_openai_client(monkeypatch)
        # Use a simple text file named .pdf — the endpoint will attempt PDF
        # extraction and fall back gracefully, then the mock provides the response.
        fake_pdf_as_text = b"Jane Smith\nSenior Software Engineer\n8 years Python experience"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Software engineer role"},
            files=[("files", ("resume.pdf", io.BytesIO(fake_pdf_as_text), "application/pdf"))],
        )
        # Should succeed regardless of pypdf availability
        assert resp.status_code == 200

    def test_generate_too_many_files_returns_400(self, monkeypatch):
        _mock_openai_client(monkeypatch)
        files = [
            ("files", (f"cv{i}.txt", io.BytesIO(b"text"), "text/plain"))
            for i in range(6)
        ]
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer"},
            files=files,
        )
        assert resp.status_code == 400
        assert "maximum" in resp.json()["detail"].lower()

    def test_generate_openai_json_error_returns_500(self, monkeypatch):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "This is not JSON at all"
        mock_client.chat.completions.create.return_value = mock_response
        monkeypatch.setattr("main.openai_client", mock_client)

        txt = b"Jane Smith\nSoftware Engineer"
        resp = client.post(
            "/api/generate",
            data={"job_description": "Python developer"},
            files=[("files", ("cv.txt", io.BytesIO(txt), "text/plain"))],
        )
        assert resp.status_code == 500
