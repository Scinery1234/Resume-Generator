"""End-to-end test of /api/agent/* against a local mock of the Anthropic API.

The mock streams a real Messages API event sequence, so this exercises the
Anthropic SDK call in resume_agent/claude.py as well as the routes.
"""
import base64
import io
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from docx import Document

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_temp.db")
FIX = os.path.join(os.path.dirname(__file__), "fixtures")
APPROVED = json.load(open(os.path.join(FIX, "approved_resume.json")))
SOURCE = open(os.path.join(FIX, "source_resume.txt")).read()


class MockAnthropic(BaseHTTPRequestHandler):
    requests = []
    reply = {"status": "draft", "questions": [], "resume": APPROVED, "verification_notes": []}
    stop_reason = "end_turn"
    reject = None  # function(body, headers) -> error message for a 400, or None
    prefix_text = ""  # prose before the JSON (as a model may write without structured outputs)

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        MockAnthropic.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
        why = MockAnthropic.reject and MockAnthropic.reject(body, dict(self.headers))
        if why:
            raw = json.dumps({"type": "error", "error": {"type": "invalid_request_error", "message": why}}).encode()
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        text = MockAnthropic.prefix_text + json.dumps(MockAnthropic.reply)
        events = [
            ("message_start", {"type": "message_start", "message": {"id": "msg_1", "type": "message", "role": "assistant", "model": body["model"], "content": [], "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 1}}}),
            ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}),
            ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[:50]}}),
            ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[50:]}}),
            ("content_block_stop", {"type": "content_block_stop", "index": 0}),
            ("message_delta", {"type": "message_delta", "delta": {"stop_reason": MockAnthropic.stop_reason, "stop_sequence": None}, "usage": {"output_tokens": 500}}),
            ("message_stop", {"type": "message_stop"}),
        ]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for name, data in events:
            self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode())


@pytest.fixture(scope="module")
def client():
    server = HTTPServer(("127.0.0.1", 0), MockAnthropic)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    old = {k: os.environ.get(k) for k in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    os.environ["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    from fastapi.testclient import TestClient
    from main import app
    yield TestClient(app)
    server.shutdown()
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_status(client):
    r = client.get("/api/agent/status").json()
    assert r["ai"] is True and r["model"] == "claude-opus-5-5"


def test_job_description_pdf_upload(client):
    with open(os.path.join(FIX, "job_description.pdf"), "rb") as f:
        r = client.post("/api/agent/extract", files={"file": ("job.pdf", f, "application/pdf")})
    assert r.status_code == 200, r.text
    assert "Operations Manager" in r.json()["text"] and "Manhattan WMS" in r.json()["text"]
    bad = client.post("/api/agent/extract", files={"file": ("job.exe", b"MZ", "application/octet-stream")})
    assert bad.status_code == 422


def test_full_flow_through_the_api(client):
    MockAnthropic.requests.clear()
    jd = "Operations Manager, distribution centre. Lead teams, WMS, WHS, stakeholder engagement, peak planning."
    r = client.post("/api/agent/start", json={"materials": SOURCE, "job_description": jd, "target_title": "Operations Manager"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["state"] == "AWAITING_CONTENT_APPROVAL" and out["messages"][0]["kind"] == "draft"

    req = MockAnthropic.requests[0]
    body = req["body"]
    assert req["path"].startswith("/v1/messages")
    assert body["model"] == "claude-opus-5-5" and body["stream"] is True
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["output_config"]["format"]["schema"]["required"] == ["status", "questions", "resume", "verification_notes"]
    assert "tool_choice" not in body and "tools" not in body and "thinking" not in body
    assert body["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in req["headers"].get("anthropic-beta", "")
    assert "<job_description>" in body["messages"][0]["content"] and "Jordan Smith" in body["messages"][0]["content"]

    out = client.post("/api/agent/reply", json={"session": out["session"], "message": "Yes"}).json()
    assert json.loads(out["messages"][0]["json"]) == APPROVED
    res = out["messages"][1]
    assert out["state"] == "COMPLETED" and res["ok"], res["message"]
    assert res["message"] == "Jordan_Smith_Operations_Manager_Resume.docx successfully generated."
    doc = Document(io.BytesIO(base64.b64decode(res["docx"])))
    assert doc.paragraphs[0].text == "JORDAN SMITH"


def test_bad_session_and_refusal(client):
    assert client.post("/api/agent/reply", json={"session": "abc.def", "message": "Y"}).status_code == 401
    MockAnthropic.stop_reason = "refusal"
    try:
        r = client.post("/api/agent/start", json={"materials": SOURCE})
        assert r.status_code == 422 and "couldn't work with" in r.json()["detail"]
    finally:
        MockAnthropic.stop_reason = "end_turn"


def test_open_saved_legacy_resume(client):
    r = client.post("/api/agent/open", json={"resume": {"name": "Ana Lee", "contact": {"email": "a@b.co"}, "summary": "S.", "experience": []}})
    assert r.status_code == 200 and r.json()["state"] == "AWAITING_CONTENT_APPROVAL"


def _start(client):
    return client.post("/api/agent/start", json={"materials": SOURCE})


def test_rejected_options_are_retried_with_less(client):
    """An account without the fallback beta, or without structured outputs, still gets a draft."""
    MockAnthropic.requests.clear()
    MockAnthropic.reject = lambda body, h: "fallbacks: not available for this organization" if "fallbacks" in body else None
    try:
        r = _start(client)
        assert r.status_code == 200, r.text
        assert "fallbacks" in MockAnthropic.requests[0]["body"] and "fallbacks" not in MockAnthropic.requests[1]["body"]
        assert MockAnthropic.requests[1]["body"]["output_config"]["format"]["type"] == "json_schema"

        MockAnthropic.requests.clear()
        MockAnthropic.reject = lambda body, h: "bad" if "fallbacks" in body or "format" in body.get("output_config", {}) else None
        MockAnthropic.prefix_text = "Here is the resume:\n"
        r = _start(client)
        assert r.status_code == 200, r.text
        last = MockAnthropic.requests[-1]["body"]
        assert "format" not in last["output_config"] and "JSON Schema" in last["system"]

        MockAnthropic.requests.clear()
        MockAnthropic.prefix_text = ""
        MockAnthropic.reject = lambda body, h: "model: claude-opus-5-5 not found" if body["model"] == "claude-opus-5-5" else None
        r = _start(client)
        assert r.status_code == 200 and MockAnthropic.requests[-1]["body"]["model"] == "claude-sonnet-5-5"
    finally:
        MockAnthropic.reject = None
        MockAnthropic.prefix_text = ""


def test_unrecoverable_error_says_why(client):
    MockAnthropic.reject = lambda body, h: "max_tokens: too large"
    try:
        r = _start(client)
        assert r.status_code == 502
        assert "Details:" in r.json()["detail"] and "max_tokens: too large" in r.json()["detail"]
    finally:
        MockAnthropic.reject = None


def test_out_of_credit_stops_at_once(client):
    MockAnthropic.requests.clear()
    MockAnthropic.reject = lambda body, h: "Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits."
    try:
        r = _start(client)
        assert r.status_code == 503 and "run out of credit" in r.json()["detail"]
        assert len(MockAnthropic.requests) == 1
    finally:
        MockAnthropic.reject = None
