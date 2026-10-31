"""Acceptance tests for the resume agent (docs/RESUME_AGENT_SPEC.md section 17).

Claude is replaced by a fake that returns the fixture draft, so these run
offline. The Word document is really generated, executed and validated.
"""
import base64
import copy
import io
import json
import os

import pytest
from docx import Document

from resume_agent import agent, lint
from resume_agent.execute import execute_python, generate_document, validate_docx
from resume_agent.extract import extract_text
from resume_agent.filename import sanitise_filename
from resume_agent.schema import EMPTY_RESUME, RESUME_JSON_SCHEMA, from_legacy, normalise, to_json, validate
from resume_agent.workflow import (APPROVE_PROMPT, EXECUTE_PROMPT, PHASE2_HEADING, State, advance,
                                   classify_content_reply, classify_execution_reply)

HERE = os.path.dirname(__file__)
FIX = os.path.join(HERE, "fixtures")
SECRET = "test-secret"
APPROVED = json.load(open(os.path.join(FIX, "approved_resume.json")))
SOURCE = open(os.path.join(FIX, "source_resume.txt")).read()
REPLIES = json.load(open(os.path.join(FIX, "replies.json")))


class FakeClaude:
    """Returns the fixture draft; records every prompt it was sent."""

    def __init__(self, status="draft", resume=None, questions=None):
        self.calls = []
        self.status, self.resume, self.questions = status, resume or copy.deepcopy(APPROVED), questions or []

    def __call__(self, system, prompt, schema):
        self.calls.append(prompt)
        assert "Australian English" in system and schema["additionalProperties"] is False
        r = copy.deepcopy(self.resume)
        if "requested_amendments" in prompt and "retail" in prompt:
            r["professional_summary"] = r["professional_summary"].replace("Operations manager", "Retail operations manager")
        status, questions = self.status, self.questions
        if "candidate_answers_to_your_questions" in prompt:
            status, questions = "draft", []
        return {"status": status, "questions": questions, "resume": r, "verification_notes": ["Confirm the 45-person team size."]}


def test_full_workflow_gates_and_document():
    fake = FakeClaude()
    out = agent.start(SOURCE, SECRET, job_description="Operations Manager, distribution centre", target_title="Operations Manager", ask=fake)
    assert out["state"] == State.AWAITING_CONTENT_APPROVAL
    [msg] = out["messages"]
    assert msg["kind"] == "draft" and msg["prompt"] == APPROVE_PROMPT
    assert "JORDAN SMITH" in msg["text"] and "PROFESSIONAL EXPERIENCE" in msg["text"]
    assert "{" not in msg["text"], "no JSON before approval"

    # Ambiguous reply: ask again, nothing changes, no model call.
    calls = len(fake.calls)
    out = agent.reply(out["session"], "okay", SECRET, ask=fake)
    assert out["state"] == State.AWAITING_CONTENT_APPROVAL and out["messages"] == [{"kind": "text", "text": APPROVE_PROMPT}]
    assert len(fake.calls) == calls

    # "Okay" followed by a change is an amendment: full redraft, approval asked again.
    out = agent.reply(out["session"], "Okay but change the summary to mention retail", SECRET, ask=fake)
    assert out["state"] == State.AWAITING_CONTENT_APPROVAL
    assert out["messages"][0]["kind"] == "draft" and out["messages"][0]["prompt"] == APPROVE_PROMPT
    assert "Retail operations manager" in out["messages"][0]["text"]
    assert "requested_amendments" in fake.calls[-1]
    approved = out["resume"]

    # Approval: Phase 2 JSON, exact wording, strict and unfenced, then the Y prompt.
    out = agent.reply(out["session"], "Yes", SECRET, ask=fake)
    assert out["state"] == State.AWAITING_EXECUTION_APPROVAL
    [msg] = out["messages"]
    assert msg["kind"] == "json" and msg["heading"] == PHASE2_HEADING and msg["prompt"] == EXECUTE_PROMPT
    assert not msg["json"].startswith("```") and "```" not in msg["json"]
    parsed = json.loads(msg["json"])
    assert parsed == approved and validate(parsed) == []
    assert list(parsed) == list(EMPTY_RESUME)

    # Not a Y: ask again, do not run anything.
    out = agent.reply(out["session"], "maybe", SECRET, ask=fake)
    assert out["state"] == State.AWAITING_EXECUTION_APPROVAL and out["messages"][0]["text"] == EXECUTE_PROMPT

    # Y: script generated, executed, validated, file returned in the same turn.
    out = agent.reply(out["session"], "Y", SECRET, ask=fake)
    assert out["state"] == State.COMPLETED
    [res] = out["messages"]
    assert res["ok"] and res["filename"] == "Jordan_Smith_Operations_Manager_Resume.docx"
    assert res["message"] == "Jordan_Smith_Operations_Manager_Resume.docx successfully generated."
    assert res["validation"]["ok"] and res["attempts"][0]["exit_code"] == 0
    assert "from docx import Document" in res["script"] and "def add_bottom_border" in res["script"]
    doc = Document(io.BytesIO(base64.b64decode(res["docx"])))
    assert doc.paragraphs[0].text == "JORDAN SMITH"
    assert "Retail operations manager" in "\n".join(p.text for p in doc.paragraphs)

    # After completion, an amendment reopens the draft for approval.
    out = agent.reply(out["session"], "Please shorten the summary", SECRET, ask=fake)
    assert out["state"] == State.AWAITING_CONTENT_APPROVAL


def test_amendment_at_execution_gate_returns_to_drafting():
    fake = FakeClaude()
    out = agent.start(SOURCE, SECRET, ask=fake)
    out = agent.reply(out["session"], "Approved", SECRET, ask=fake)
    out = agent.reply(out["session"], "Actually change the summary first", SECRET, ask=fake)
    assert out["state"] == State.AWAITING_CONTENT_APPROVAL and out["messages"][0]["kind"] == "draft"


def test_questions_when_essential_information_is_missing():
    fake = FakeClaude(status="questions", questions=["What are your employment dates at Coastline Logistics?"])
    out = agent.start(SOURCE, SECRET, ask=fake)
    assert out["state"] == State.DRAFTING and out["messages"][0]["kind"] == "questions"
    # "Yes" cannot skip the questions: it is treated as the answer and a full draft follows.
    out = agent.reply(out["session"], "March 2019 to now", SECRET, ask=fake)
    assert out["state"] == State.AWAITING_CONTENT_APPROVAL and "candidate_answers_to_your_questions" in fake.calls[-1]


def test_session_cannot_be_forged_or_skip_gates():
    out = agent.start(SOURCE, SECRET, ask=FakeClaude())
    body, sig = out["session"].rsplit(".", 1)
    with pytest.raises(agent.AgentError):
        agent.reply(body + "." + "0" * len(sig), "Y", SECRET, ask=FakeClaude())
    with pytest.raises(agent.AgentError):
        agent.reply(out["session"], "Y", "another-secret", ask=FakeClaude())
    # "Y" at the content gate is approval of content only: it produces JSON, never a document.
    nxt = agent.reply(out["session"], "Y", SECRET, ask=FakeClaude())
    assert nxt["state"] == State.AWAITING_EXECUTION_APPROVAL and nxt["messages"][0]["kind"] == "json"


def test_short_materials_rejected():
    with pytest.raises(agent.AgentError):
        agent.start("too short", SECRET, ask=FakeClaude())


def test_lint_repair_pass_runs_and_reports_leftovers():
    bad = copy.deepcopy(APPROVED)
    bad["professional_experience"][0]["achievements"][0] = "Grew revenue by 18% across 12 sites."
    fake = FakeClaude(resume=bad)
    out = agent.start(SOURCE, SECRET, ask=fake)
    assert "<problems>" in fake.calls[1] and "18%" in fake.calls[1]
    assert any("18%" in n for n in out["messages"][0]["notes"])


@pytest.mark.parametrize("kind", ["approve", "amend", "unclear"])
def test_content_reply_classification(kind):
    for text in REPLIES["content"][kind]:
        assert classify_content_reply(text) == kind, text


@pytest.mark.parametrize("kind", ["execute", "amend", "unclear"])
def test_execution_reply_classification(kind):
    for text in REPLIES["execution"][kind]:
        assert classify_execution_reply(text) == kind, text


def test_state_machine_rejects_skips():
    with pytest.raises(ValueError):
        advance(State.AWAITING_CONTENT_APPROVAL, "execute")
    with pytest.raises(ValueError):
        advance(State.DRAFTING, "json_ready")
    assert advance(State.EXECUTION_FAILED, "retry") == State.GENERATING_SCRIPT


def test_schema_and_json():
    d = normalise({"candidate": {"full_name": " Sam  Lee "}, "awards": [{"award_name": ""}], "key_skills": ["A", ""], "junk": 1})
    assert d["candidate"]["full_name"] == "Sam Lee" and d["awards"] == [] and d["key_skills"] == ["A"] and "junk" not in d
    assert validate(d) == []
    assert json.loads(to_json(d)) == d
    assert validate({**d, "awards": None}) and validate({**d, "extra": []}) and validate({})
    assert RESUME_JSON_SCHEMA["properties"]["professional_experience"]["items"]["required"][-1] == "achievements"
    legacy = from_legacy({"name": "Ana", "contact": {"email": "a@b.co"}, "summary": "S.", "experience": [{"title": "Nurse", "company": "RPA", "dates": "Jan 2020 – Present", "bullets": ["Did x"]}], "technical_skills": {"Tools": ["Excel"]}})
    assert legacy["professional_experience"][0]["start_date"] == "Jan 2020" and legacy["professional_experience"][0]["end_date"] == "Present"
    assert legacy["technical_skills"] == [{"category": "Tools", "skills": ["Excel"]}]


def test_filename_rules():
    assert sanitise_filename("Jordan Smith", "Operations Manager") == "Jordan_Smith_Operations_Manager_Resume.docx"
    assert sanitise_filename("Sam", "") == "Sam_Professional_Resume.docx"
    assert sanitise_filename("Sam", "", "Nurse") == "Sam_Nurse_Resume.docx"
    name = sanitise_filename('A<b>:c"/\\|?*', "  Head of / People  ")
    assert not any(ch in name for ch in '<>:"/\\|?* ') and "__" not in name
    assert len(sanitise_filename("A" * 300, "B" * 300)) <= 130


def test_document_formatting(tmp_path):
    r = generate_document(APPROVED, keep_dir=True)
    assert r["ok"], r["message"]
    path = os.path.join(r["workdir"], r["filename"])
    doc = Document(path)
    s = doc.sections[0]
    assert round(s.page_width.cm, 1) == 21.0 and round(s.page_height.cm, 1) == 29.7
    assert doc.tables == [] and doc.styles["Normal"].font.name == "Calibri"
    name = doc.paragraphs[0]
    assert name.alignment == 1 and name.runs[0].bold and name.runs[0].font.size.pt == 22
    assert any(p.style.name == "List Bullet" for p in doc.paragraphs)
    assert "w:hyperlink" not in doc.element.xml
    assert {c["name"] for c in r["validation"]["checks"] if not c["ok"]} == set()
    # Optional sections are left out when empty.
    empty = normalise({**APPROVED, "awards": [], "certifications": [], "additional_information": []})
    r2 = generate_document(empty, visual=False)
    text = "\n".join(p.text for p in Document(io.BytesIO(r2["docx"])).paragraphs)
    assert "AWARDS" not in text and "CERTIFICATIONS" not in text and "ADDITIONAL INFORMATION" not in text


def test_awkward_text_still_builds():
    d = copy.deepcopy(APPROVED)
    d["candidate"]["full_name"] = "Zoë O'Brien-Nguyễn"
    d["professional_summary"] = "Leads teams\x0b with \"quotes\", 'apostrophes', __DATA__ and ''' triple quotes. Second sentence. Third sentence."
    r = generate_document(d, visual=False)
    assert r["ok"], r["message"]
    assert r["filename"] == "Zoë_O'Brien-Nguyễn_Operations_Manager_Resume.docx"


def test_failure_is_reported_honestly(monkeypatch):
    import resume_agent.execute as ex
    monkeypatch.setattr(ex, "build_script", lambda data, fb="": "import sys\nsys.exit('boom')\n")
    r = ex.generate_document(APPROVED, visual=False)
    assert not r["ok"] and "docx" not in r and r["state"] == "EXECUTION_FAILED"
    assert len(r["attempts"]) == 2 and "successfully generated" not in r["message"]


def test_validator_catches_bad_documents(tmp_path):
    from docx.shared import Pt, RGBColor
    doc = Document()
    p = doc.add_paragraph("Jordan Smith")
    p.runs[0].font.color.rgb = RGBColor(0, 0, 255)
    p.runs[0].font.size = Pt(14)
    doc.add_table(rows=1, cols=2)
    path = str(tmp_path / "bad.docx")
    doc.save(path)
    failed = {c["name"] for c in validate_docx(path, normalise(APPROVED))["checks"] if not c["ok"]}
    assert {"No tables", "All text black", "Name: uppercase, centred, bold, 22 pt", "A4 page size"} <= failed


def test_execute_python_contract():
    r = execute_python("print('hi')", "x.docx")
    assert r["exit_code"] == 0 and r["stdout"].strip() == "hi" and r["files"] == []


def test_extract_text_from_pdf_and_docx(tmp_path):
    r = generate_document(APPROVED, visual=False)
    assert "Coastline Logistics" in extract_text("cv.docx", r["docx"])
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    assert extract_text("jd.pdf", buf.getvalue()) == ""
    with pytest.raises(ValueError):
        extract_text("jd.pdf", b"not a pdf")
    with pytest.raises(ValueError):
        extract_text("a.exe", b"x")


def test_integrity_lint_flags_invented_facts():
    d = normalise(APPROVED)
    assert lint.integrity_issues(d, SOURCE) == [] and lint.quality_issues(d) == []
    d["professional_experience"][0]["employer"] = "Globex Corporation"
    d["key_skills"][0] = "Leadership & Management"
    assert any("Globex" in i for i in lint.integrity_issues(d, SOURCE))
    assert any("ampersand" in i for i in lint.quality_issues(d))
