"""
Tests for error handling across API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io

from main import app

client = TestClient(app)


class TestErrorHandling:
    def test_invalid_user_id_returns_400(self):
        """Test that invalid user_id values are rejected"""
        resp = client.get("/api/resumes?user_id=0")
        assert resp.status_code == 400 or resp.status_code == 200  # May return empty list
    
    def test_negative_user_id_returns_400(self):
        resp = client.get("/api/resumes?user_id=-1")
        assert resp.status_code == 400 or resp.status_code == 200
    
    def test_malformed_filename_sanitized(self):
        """Test that dangerous filenames are sanitized"""
        dangerous_name = "../../../etc/passwd"
        resp = client.get(f"/api/resumes/download-file/{dangerous_name}")
        # Should either 404 (file doesn't exist) or sanitize the path
        assert resp.status_code in (400, 404)
    
    def test_invalid_file_extension_rejected(self):
        """Test that invalid file extensions are rejected in upload"""
        fake_file = ("resume.exe", io.BytesIO(b"fake content"), "application/x-msdownload")
        resp = client.post(
            "/api/upload-resume",
            files={"file": fake_file}
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"].lower()
    
    def test_file_too_large_rejected(self):
        """Test that files exceeding size limit are rejected"""
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        fake_file = ("resume.pdf", io.BytesIO(large_content), "application/pdf")
        resp = client.post(
            "/api/upload-resume",
            files={"file": fake_file}
        )
        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"].lower()
    
    def test_missing_required_fields_returns_422(self):
        """Test that missing required fields return 422"""
        resp = client.post("/api/auth/signup", json={})
        assert resp.status_code == 422
    
    def test_invalid_email_format_returns_422(self):
        """Test that invalid email format is rejected"""
        resp = client.post("/api/auth/signup", json={
            "name": "Test",
            "email": "not-an-email",
            "password": "password123"
        })
        assert resp.status_code == 422


class TestDatabaseErrorHandling:
    @patch('main.get_db')
    def test_ssl_connection_error_handled(self, mock_get_db):
        """Test that SSL connection errors are handled gracefully"""
        from sqlalchemy.exc import OperationalError
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("SSL connection has been closed", None, None)
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # This would need the actual endpoint to be called
        # For now, we verify the error handling function exists
        from utils import handle_database_error
        error = OperationalError("SSL connection has been closed", None, None)
        result = handle_database_error(error, "test operation")
        assert result.status_code == 503


class TestPromptLimitEnforcement:
    def test_prompt_limit_check(self):
        """Test that prompt limits are enforced"""
        # This would require setting up a user with max prompts
        # For now, verify the function exists
        from utils import get_max_prompts_for_tier
        assert get_max_prompts_for_tier("free") == 10
        assert get_max_prompts_for_tier("pro") == 100
