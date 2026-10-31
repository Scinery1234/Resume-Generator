"""HTTP API for the four-phase resume agent (docs/RESUME_AGENT_SPEC.md).

  GET  /api/agent/status                 -> {ai, model, rendering}
  POST /api/agent/extract  (multipart)   -> {text}            resume, JD (PDF/Word/text), notes
  POST /api/agent/start    {materials, job_description, target_title, additional}
  POST /api/agent/reply    {session, message}
  POST /api/agent/open     {resume, ...} -> reopen a saved resume at the approval gate

start/reply/open return {state, session, messages, resume}. `session` is
signed; the browser sends it back unchanged with each reply.
"""
import logging
import os
import secrets
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from resume_agent import agent
from resume_agent.claude import ClaudeError, model_name
from resume_agent.extract import extract_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["Resume Agent"])

MAX_UPLOAD = 5 * 1024 * 1024
_SECRET = os.getenv("RESUME_SESSION_SECRET") or os.getenv("SECRET_KEY")
if not _SECRET:
    # Sessions then last only as long as this process. Set RESUME_SESSION_SECRET in production.
    _SECRET = secrets.token_hex(32)
    logger.warning("RESUME_SESSION_SECRET is not set; resume sessions reset when the server restarts")

CLAUDE_ERRORS = {
    "unavailable": (503, "The resume writer isn't switched on yet (ANTHROPIC_API_KEY is not set)."),
    "billing": (503, "The resume writer is unavailable: the Anthropic account behind it has run out of credit. The site owner needs to add credit in the Anthropic Console (Plans & Billing)."),
    "rate_limited": (429, "The writer is busy right now. Please try again in a minute."),
    "overloaded": (503, "The writer is busy right now. Please try again in a minute."),
    "refused": (422, "The writer couldn't work with that material. Check it is a resume or career notes and try again."),
    "truncated": (502, "The draft was too long to finish. Try trimming very old roles from your materials."),
    "error": (502, "The writer couldn't finish the draft. Please try again."),
}


def ai_configured():
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


class StartBody(BaseModel):
    materials: str = Field(..., max_length=60000)
    job_description: str = Field("", max_length=30000)
    target_title: str = Field("", max_length=200)
    additional: str = Field("", max_length=6000)


class ReplyBody(BaseModel):
    session: str = Field(..., max_length=400000)
    message: str = Field("", max_length=6000)


class OpenBody(BaseModel):
    resume: dict
    materials: str = Field("", max_length=60000)
    job_description: str = Field("", max_length=30000)
    target_title: str = Field("", max_length=200)


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except agent.AgentError as e:
        raise HTTPException(status_code=401 if e.code == "session" else 400, detail=str(e))
    except ClaudeError as e:
        status, msg = CLAUDE_ERRORS.get(e.code, CLAUDE_ERRORS["error"])
        logger.error("Resume agent Claude call failed (%s): %s", e.code, e)
        if e.code == "error":
            # Say why, so a setup problem (API key, model access) can be seen without the server log.
            msg = f"{msg} (Details: {str(e)[:400]})"
        raise HTTPException(status_code=status, detail=msg)


@router.get("/status")
def status():
    return {"ai": ai_configured(), "model": model_name(), "rendering": bool(shutil.which("soffice") or shutil.which("libreoffice"))}


@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="That file is over 5 MB. Try a smaller file, or paste the text.")
    try:
        text = extract_text(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if len(text.strip()) < 40:
        raise HTTPException(status_code=422, detail="We couldn't read any text in that file. If it's a scan or a picture, paste the text instead.")
    return {"text": text, "filename": file.filename}


@router.post("/start")
def start(body: StartBody):
    return _run(agent.start, body.materials, _SECRET, job_description=body.job_description,
                target_title=body.target_title, additional=body.additional)


@router.post("/reply")
def reply(body: ReplyBody):
    return _run(agent.reply, body.session, body.message, _SECRET)


@router.post("/open")
def open_saved(body: OpenBody):
    return _run(agent.resume_session, body.resume, _SECRET, materials=body.materials,
                job_description=body.job_description, target_title=body.target_title)
