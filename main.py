import io
import os
from fastapi import FastAPI, Form, HTTPException, UploadFile, File, Depends, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from openai import OpenAI
from dotenv import load_dotenv
import json
import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db, init_db
from models import User, Resume
from doc_builder import ResumeBuilder, TEMPLATE_LIST, DUMMY_CANDIDATE
from prompts import SYSTEM_PROMPT_DRAFT, SYSTEM_PROMPT_GENERATE, create_resume_prompt, build_generate_prompt
from utils import (
    sanitize_filename, validate_file_extension, get_max_prompts_for_tier,
    handle_database_error, standardize_response, validate_user_id,
    MAX_FILES, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, MAX_PROMPTS_GUEST
)
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Only create the OpenAI client if a real API key is set (not the placeholder)
_raw_openai_key = os.getenv("OPENAI_API_KEY", "")
_openai_key_is_real = bool(_raw_openai_key) and not _raw_openai_key.startswith("your_")
openai_client = OpenAI(api_key=_raw_openai_key) if _openai_key_is_real else None
if not _openai_key_is_real:
    logger.warning("OPENAI_API_KEY is not configured — AI generation will be unavailable")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Initialize database
init_db()

# Seed demo user on startup (idempotent – skipped if already present)
def seed_demo_user():
    import hashlib, json
    from database import SessionLocal
    DEMO_EMAIL = "demo@example.com"
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == DEMO_EMAIL).first():
            return
        skills = json.dumps(["Python", "JavaScript", "React", "FastAPI",
                              "SQL", "REST APIs", "Git", "Docker"])
        experience = json.dumps([
            {"company": "Acme Corp", "title": "Software Engineer",
             "start_date": "2021-06", "end_date": "Present",
             "description": ("Built and maintained full-stack web applications using React "
                             "and FastAPI. Reduced page load time by 40% through code "
                             "splitting and caching optimisations.")},
            {"company": "Startup Inc.", "title": "Junior Developer",
             "start_date": "2019-08", "end_date": "2021-05",
             "description": ("Developed REST APIs and automated reporting pipelines. "
                             "Collaborated with the design team to ship three major product features.")},
        ])
        education = json.dumps([
            {"institution": "State University", "degree": "B.S. Computer Science",
             "start_date": "2015-09", "end_date": "2019-05", "gpa": "3.8"}
        ])
        summary = ("Results-driven software engineer with 5+ years of experience building "
                   "scalable web applications. Passionate about clean code, developer "
                   "experience, and delivering user-friendly products.")
        user = User(
            name="Alex Demo", email=DEMO_EMAIL,
            password_hash=hashlib.sha256(b"demo1234").hexdigest(),
            professional_summary=summary, skills=skills,
            experience=experience, education=education,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()
        contact_info = json.dumps({"name": "Alex Demo", "email": DEMO_EMAIL,
                                   "phone": "555-0100", "location": "San Francisco, CA",
                                   "linkedin": "linkedin.com/in/alex-demo",
                                   "github": "github.com/alex-demo"})
        db.add(Resume(
            user_id=user.id, name="Alex Demo – Software Engineer",
            professional_summary=summary, skills=skills,
            experience=experience, education=education,
            contact_info=contact_info,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        ))
        db.commit()
        logger.info("Demo user seeded: demo@example.com / demo1234")
    except Exception as exc:
        db.rollback()
        logger.warning("Could not seed demo user: %s", exc)
    finally:
        db.close()

seed_demo_user()

# Security
security = HTTPBearer()


def resolve_template_id(template_id: Optional[str]) -> str:
    """Return a known template id, accepting ids or names."""
    normalized = (template_id or "modern").strip().lower()
    template_lookup = {
        t["id"].strip().lower(): t["id"]
        for t in TEMPLATE_LIST
    }
    template_lookup.update({
        t["name"].strip().lower(): t["id"]
        for t in TEMPLATE_LIST
    })
    return template_lookup.get(normalized, "modern")

# FastAPI app initialization
app = FastAPI(
    title="Resume Generator API",
    version="1.0.0",
    description="Production-ready FastAPI application for generating professional resumes"
)

# Add CORS middleware
# CORS_ORIGINS can be "*" to allow all origins (e.g. during development or
# when the frontend domain isn't known yet), or a comma-separated list of
# allowed origins for production (e.g. "https://your-app.vercel.app").
# Note: allow_credentials cannot be True when origins is "*".
_cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]

# Handle wildcard for development/testing
# If CORS_ORIGINS is "*", allow all origins but disable credentials
if _cors_origins == ["*"]:
    _allow_origins = ["*"]
    _allow_credentials = False
else:
    _allow_origins = _cors_origins
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers for CORS
)

# File upload configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
RESUMES_DIR = Path(os.getenv("RESUMES_DIR", "./resumes"))
UPLOAD_DIR.mkdir(exist_ok=True)
RESUMES_DIR.mkdir(exist_ok=True)
# Note: MAX_FILES, MAX_FILE_SIZE, ALLOWED_EXTENSIONS are now in utils.py

# Pydantic Models
class ContactInfo(BaseModel):
    email: EmailStr
    phone: str
    location: str
    linkedin: Optional[str] = None

class ExperienceItem(BaseModel):
    title: str
    company: str
    location: str
    dates: str
    description: str = ""
    bullets: List[str] = []

class EducationItem(BaseModel):
    degree: str
    institution: str
    # New schema uses "year"; old schema used "graduation_year" — both accepted
    year: Optional[str] = ""
    graduation_year: Optional[str] = ""  # kept for backward compatibility
    field: Optional[str] = ""            # kept for backward compatibility

class CandidateInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    contact: ContactInfo
    # New schema uses "summary"; old schema used "professional_summary" — both accepted
    summary: Optional[str] = Field(default="", max_length=2000)
    professional_summary: Optional[str] = Field(default="", max_length=2000)
    key_skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    technical_skills: Optional[object] = Field(default_factory=list)  # dict or list
    additional_information: Optional[List[str]] = Field(default_factory=list)
    user_id: Optional[int] = None

class UserSignup(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ResumeResponse(BaseModel):
    resume_id: int
    name: str
    created_at: str
    file_path: Optional[str] = None

# Routes
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - Health check"""
    return {
        "message": "Resume Generator API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Resume Generator API",
        "timestamp": datetime.utcnow().isoformat()
    }

# Helper function to get current user (simplified - in production use JWT)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    # Simplified auth - in production, decode JWT token
    # For now, we'll use a simple token check
    user = db.query(User).filter(User.id == int(credentials.credentials)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

@app.post("/api/auth/signup", tags=["Authentication"])
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        new_user = User(
            name=user_data.name,
            email=user_data.email,
            password_hash=User.hash_password(user_data.password)
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "status": "success",
            "message": "User created successfully",
            "user_id": new_user.id,
            "token": str(new_user.id)  # Simplified - use JWT in production
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.post("/api/auth/login", tags=["Authentication"])
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    try:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not user.verify_password(login_data.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        return standardize_response({
            "message": "Login successful",
            "user_id": user.id,
            "token": str(user.id)  # Simplified - use JWT in production
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error logging in: {str(e)}")

# ── PDF library availability check (done once at import time) ────────────────
# pypdf depends on the cryptography package which can have system-level issues.
# We pre-check here so extraction code can skip it gracefully if unavailable.
try:
    from pypdf import PdfReader as _PdfReader
    _PYPDF_AVAILABLE = True
except BaseException as _pdf_import_err:
    _PdfReader = None
    _PYPDF_AVAILABLE = False
    logger.warning("pypdf import failed (%s) — PDF text extraction will fall back to raw decode", _pdf_import_err)


# ── Text extraction helpers ──────────────────────────────────────────────────

async def extract_text_from_upload(file: UploadFile) -> str:
    """Extract plain text from an uploaded file (TXT, DOCX, PDF)."""
    content = await file.read()
    name = (file.filename or "").lower()

    if name.endswith(".txt") or file.content_type in ("text/plain",):
        return content.decode("utf-8", errors="ignore")

    if name.endswith(".docx") or "wordprocessingml" in (file.content_type or ""):
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except BaseException as exc:
            logger.warning("DOCX extraction failed for %s: %s", file.filename, exc)
            return content.decode("utf-8", errors="ignore")

    if name.endswith(".pdf") or file.content_type == "application/pdf":
        if _PYPDF_AVAILABLE and _PdfReader is not None:
            try:
                reader = _PdfReader(io.BytesIO(content))
                pages_text = [page.extract_text() for page in reader.pages]
                text = "\n".join(t for t in pages_text if t)
                if text.strip():
                    return text
            except BaseException as exc:
                logger.warning("PDF extraction failed for %s: %s", file.filename, exc)
        # Fall back: PDFs sometimes contain embedded text readable as bytes
        return content.decode("utf-8", errors="ignore")

    # Unknown type — try UTF-8 decode as a last resort
    return content.decode("utf-8", errors="ignore")


# ── Primary endpoint: generate from uploaded documents + job description ─────

@app.post("/api/generate", tags=["Resume Generation"])
async def generate_from_documents(
    files: List[UploadFile] = File(default=[]),
    job_description: str = Form(default=""),
    additional_info: str = Form(default=""),
    template: str = Form(default="modern"),
    user_id: Optional[int] = Form(default=None),  # Optional user ID for logged-in users
    db: Session = Depends(get_db),
):
    """
    Generate a tailored Australian resume from:
    - Up to 5 uploaded supporting documents (old resumes, LinkedIn exports, etc.)
    - An optional job description (omit for general-mode generation)
    - Optional additional information (responses to criteria, specific examples, etc.)

    When a job description is provided the resume is fully tailored to that role
    (customisation mode). When omitted the AI generates a strong general-purpose
    resume emphasising recency and seniority (general mode).

    Returns a .docx download URL and an HTML preview.
    """
    # Validate inputs first (before checking service availability)
    real_files = [f for f in files if f.filename]
    if not real_files:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least one supporting document (resume, LinkedIn export, etc.).",
        )
    if len(real_files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files are allowed.")

    job_description = job_description.strip()
    # job_description is now optional — empty string triggers general mode

    # Check OpenAI service availability after input validation
    if not openai_client:
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenAI API key is not configured. "
                "Please add a valid OPENAI_API_KEY to the .env file and restart the server."
            ),
        )

    # Extract text from every uploaded file
    doc_parts: List[str] = []
    for f in real_files:
        text = await extract_text_from_upload(f)
        if text.strip():
            doc_parts.append(f"--- {f.filename} ---\n{text.strip()}")

    if not doc_parts:
        raise HTTPException(
            status_code=400,
            detail="Could not extract any text from the uploaded files. "
                   "Please ensure the files contain readable text.",
        )

    documents_text = "\n\n".join(doc_parts)
    # Include additional info if provided
    additional_info_text = additional_info.strip() if additional_info else ""
    
    # Log additional info for debugging
    if additional_info_text:
        logger.info(f"Additional information provided ({len(additional_info_text)} chars): {additional_info_text[:200]}...")
    else:
        logger.info("No additional information provided")
    
    user_prompt = build_generate_prompt(documents_text, job_description, additional_info_text)
    
    generation_mode = "customisation" if job_description else "general"
    logger.info(
        "Prompt built: mode=%s, length=%d chars, additional_info=%s",
        generation_mode, len(user_prompt), bool(additional_info_text),
    )

    # Call OpenAI to generate the resume JSON
    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_GENERATE},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
            timeout=120,
        )
        resume_json_str = response.choices[0].message.content
        resume_data = json.loads(resume_json_str)
    except json.JSONDecodeError as exc:
        logger.error("OpenAI returned non-JSON: %s", exc)
        raise HTTPException(status_code=500, detail="AI returned an unexpected format. Please try again.")
    except Exception as exc:
        logger.error("OpenAI generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"AI generation failed: {exc}")

    # Build the .docx
    resume_builder = ResumeBuilder()
    resume_filename = f"resume_{uuid.uuid4().hex[:10]}.docx"
    # Sanitize filename (though UUID should be safe, this is defensive)
    safe_filename = sanitize_filename(resume_filename)
    resume_path = RESUMES_DIR / safe_filename
    resolved_template = resolve_template_id(template)
    resume_builder.build_word_document(str(resume_path), resume_data, template_id=resolved_template)

    # Build the HTML preview
    preview_html = resume_builder.build_html_preview(resume_data, template_id=resolved_template)

    # Always save the resume to the database (user_id=None for guests) so that
    # the resume_id can be used for AI-powered edits without requiring login.
    resume_id = None
    try:
        resume_record = Resume(
            user_id=user_id,  # NULL for guest resumes
            name=resume_data.get("name", "Untitled Resume"),
            file_path=str(resume_path),
            contact_info=json.dumps(resume_data.get("contact", {})),
            resume_data=json.dumps(resume_data),
            preview_html=preview_html,
            template_id=resolved_template,
        )
        db.add(resume_record)
        db.commit()
        db.refresh(resume_record)
        resume_id = resume_record.id
    except Exception as e:
        logger.error(f"Error saving resume to database: {e}")
        db.rollback()

    logger.info("Resume generated: %s (name: %s)", safe_filename, resume_data.get("name", "unknown"))
    # Return a flat response — NOT wrapped in standardize_response — so the
    # frontend can access filename, preview_html, and resume_id directly.
    return {
        "filename": safe_filename,
        "download_url": f"/api/resumes/download-file/{safe_filename}",
        "preview_html": preview_html,
        "data": resume_data,
        "resume_id": resume_id,
    }


# ── Legacy wizard endpoint (kept for backward compatibility) ──────────────────

@app.post("/api/generate-resume", tags=["Resume Generation"])
async def generate_resume(
    candidate: CandidateInput,
    db: Session = Depends(get_db)
):
    """Generate a professional resume from candidate information"""
    try:
        logger.info(f"Generating resume for {candidate.name}")
        
        # Get user_id from request body
        user_id = candidate.user_id
        
        # Convert Pydantic model to dict (exclude user_id from dict)
        candidate_dict = candidate.model_dump(exclude={'user_id'})

        # Optionally enhance with OpenAI (if API key is available)
        enhanced_summary = candidate.professional_summary
        if openai_client:
            try:
                prompt = create_resume_prompt(candidate_dict)
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_DRAFT},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                enhanced_summary = response.choices[0].message.content
            except Exception as e:
                logger.warning(f"OpenAI enhancement failed: {str(e)}, using original summary")

        # Update candidate_dict with enhanced summary before building the document
        candidate_dict['professional_summary'] = enhanced_summary

        # Build Word document
        resume_builder = ResumeBuilder()
        resume_filename = f"resume_{uuid.uuid4().hex[:8]}_{candidate.name.replace(' ', '_')}.docx"
        resume_path = RESUMES_DIR / resume_filename

        resume_builder.build_word_document(str(resume_path), candidate_dict)

        # Save to database if user_id provided
        resume_id = None
        if user_id:
            resume_record = Resume(
                user_id=user_id,
                name=candidate.name,
                file_path=str(resume_path),
                professional_summary=enhanced_summary,
                skills=json.dumps(candidate.key_skills + candidate.technical_skills),
                experience=json.dumps([exp.model_dump() for exp in candidate.experience]),
                education=json.dumps([edu.model_dump() for edu in candidate.education]),
                contact_info=json.dumps(candidate.contact.model_dump())
            )
            db.add(resume_record)
            db.commit()
            db.refresh(resume_record)
            resume_id = resume_record.id
        
        return {
            "status": "success",
            "message": "Resume generated successfully",
            "data": {
                "resume_id": resume_id,
                "name": candidate.name,
                "email": candidate.contact.email,
                "file_path": str(resume_path),
                "filename": resume_filename,
                "download_url": f"/api/resumes/download-file/{resume_filename}",
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating resume: {str(e)}")

@app.post("/api/preview-resume", tags=["Resume Generation"], response_class=HTMLResponse)
async def preview_resume(candidate: CandidateInput):
    """
    Return an HTML preview of the resume that matches the exported .docx layout.
    The frontend embeds this in an iframe (srcdoc) so users see an exact document preview.
    """
    try:
        candidate_dict = candidate.model_dump(exclude={'user_id'})
        resume_builder = ResumeBuilder()
        html_content = resume_builder.build_html_preview(candidate_dict)
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")


@app.get("/api/resumes", tags=["Resume Management"])
async def get_user_resumes(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all resumes for a user"""
    import time
    max_retries = 3
    retry_delay = 0.5
    
    # Validate user_id if provided
    if user_id is not None and not validate_user_id(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    
    for attempt in range(max_retries):
        try:
            resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
            return standardize_response({
                "resumes": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "file_path": r.file_path,
                        "contact_info": r.contact_info,
                        "filename": Path(r.file_path).name if r.file_path else None,
                    }
                    for r in resumes
                ]
            })
        except Exception as e:
            error_str = str(e)
            if "SSL connection" in error_str or "closed unexpectedly" in error_str:
                if attempt < max_retries - 1:
                    logger.warning(f"SSL connection error (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                    db.rollback()
                    continue
                else:
                    raise handle_database_error(e, "fetching resumes")
            else:
                raise handle_database_error(e, "fetching resumes")
    
    raise HTTPException(status_code=500, detail="Failed to fetch resumes after retries")

@app.get("/api/resumes/{resume_id}/download", tags=["Resume Management"])
async def download_resume(resume_id: int, db: Session = Depends(get_db)):
    """Download a resume file"""
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        if not resume.file_path or not Path(resume.file_path).exists():
            raise HTTPException(status_code=404, detail="Resume file not found")
        
        return FileResponse(
            resume.file_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{resume.name}_resume.docx"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading resume: {str(e)}")

@app.get("/api/resumes/download-file/{filename}", tags=["Resume Management"])
async def download_resume_by_filename(filename: str):
    """Download a generated resume file directly by filename"""
    try:
        # Sanitize filename to prevent directory traversal
        safe_filename = sanitize_filename(filename)
        file_path = RESUMES_DIR / safe_filename
        
        # Additional security: ensure file is within RESUMES_DIR
        try:
            file_path.resolve().relative_to(RESUMES_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Resume file not found")

        return FileResponse(
            str(file_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=safe_filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resume file: {str(e)}")
        raise HTTPException(status_code=500, detail="Error downloading resume file")

@app.delete("/api/resumes/{resume_id}", tags=["Resume Management"])
async def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    """Delete a resume"""
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Delete file if exists
        if resume.file_path and Path(resume.file_path).exists():
            Path(resume.file_path).unlink()
        
        db.delete(resume)
        db.commit()
        
        return {
            "status": "success",
            "message": "Resume deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting resume: {str(e)}")

@app.post("/api/upload-resume", tags=["File Operations"])
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume file"""
    try:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"File type {file_ext} not allowed")
        
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        logger.info(f"File uploaded successfully: {file.filename}")
        return {
            "status": "success",
            "message": "File uploaded successfully",
            "filename": file.filename,
            "file_size": len(file_content)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.post("/api/resumes/{resume_id}/edit", tags=["Resume Editing"])
async def edit_resume_with_prompt(
    resume_id: int,
    prompt: str = Form(...),
    user_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
):
    """Edit a resume using a text prompt. Checks prompt count limits.

    Guests (no user_id) may edit their resume up to MAX_PROMPTS_GUEST times.
    Logged-in users are limited by their membership tier.
    """
    if user_id:
        # ── Logged-in user ────────────────────────────────────────────────
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        max_prompts = get_max_prompts_for_tier(user.membership_tier)
        if user.prompt_count >= max_prompts:
            raise HTTPException(
                status_code=403,
                detail=f"You've reached your prompt limit ({max_prompts}). Upgrade to Pro for more edits!"
            )

        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
    else:
        # ── Guest ─────────────────────────────────────────────────────────
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id.is_(None)).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        if (resume.guest_edit_count or 0) >= MAX_PROMPTS_GUEST:
            raise HTTPException(
                status_code=403,
                detail=f"You've used all {MAX_PROMPTS_GUEST} free edits. Sign up for a paid plan to get 50 edits!"
            )
    
    if not resume.resume_data:
        raise HTTPException(status_code=400, detail="Resume data not available for editing")
    
    # Parse existing resume data
    current_data = json.loads(resume.resume_data)
    
    # Create edit prompt
    edit_prompt = f"""You are editing an existing resume. The user wants to make the following change:

USER REQUEST: {prompt}

CURRENT RESUME DATA (JSON):
{json.dumps(current_data, indent=2)}

Please update the resume JSON to reflect the requested changes. Maintain the same structure and format.
Return ONLY the updated JSON object — no other text."""
    
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI API not configured")
    
    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_GENERATE},
                {"role": "user", "content": edit_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
            timeout=120,
        )
        updated_data = json.loads(response.choices[0].message.content)

        # Update resume — preserve the template that was last applied
        active_template = resume.template_id or "modern"
        resume_builder = ResumeBuilder()
        resume_filename = f"resume_{uuid.uuid4().hex[:10]}.docx"
        resume_path = RESUMES_DIR / resume_filename
        resume_builder.build_word_document(str(resume_path), updated_data, template_id=active_template)
        preview_html = resume_builder.build_html_preview(updated_data, template_id=active_template)
        
        resume.resume_data = json.dumps(updated_data)
        resume.preview_html = preview_html
        resume.file_path = str(resume_path)
        resume.updated_at = datetime.utcnow()

        # Increment the appropriate counter and build the remaining-edits info
        if user_id:
            user.prompt_count += 1
            prompt_count = user.prompt_count
            remaining = max(0, max_prompts - prompt_count)
        else:
            resume.guest_edit_count = (resume.guest_edit_count or 0) + 1
            prompt_count = resume.guest_edit_count
            max_prompts = MAX_PROMPTS_GUEST
            remaining = max(0, MAX_PROMPTS_GUEST - prompt_count)

        db.commit()
        db.refresh(resume)

        return {
            "status": "success",
            "preview_html": preview_html,
            "data": updated_data,
            "prompt_count": prompt_count,
            "max_prompts": max_prompts,
            "remaining_prompts": remaining,
            "filename": Path(resume.file_path).name if resume.file_path else None,
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned invalid format")
    except Exception as e:
        logger.error(f"Error editing resume: {e}")
        raise HTTPException(status_code=500, detail=f"Error editing resume: {str(e)}")


@app.put("/api/resumes/{resume_id}/update", tags=["Resume Editing"])
async def update_resume_inline(
    resume_id: int,
    resume_data: dict = Body(...),
    user_id: int = Body(...),
    db: Session = Depends(get_db),
):
    """Update resume data directly (for inline editing)."""
    
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Rebuild preview and document — preserve the template that was last applied
    active_template = resume.template_id or "modern"
    resume_builder = ResumeBuilder()
    resume_filename = f"resume_{uuid.uuid4().hex[:10]}.docx"
    safe_filename = sanitize_filename(resume_filename)
    resume_path = RESUMES_DIR / safe_filename
    resume_builder.build_word_document(str(resume_path), resume_data, template_id=active_template)
    preview_html = resume_builder.build_html_preview(resume_data, template_id=active_template)
    
    resume.resume_data = json.dumps(resume_data)
    resume.preview_html = preview_html
    resume.file_path = str(resume_path)
    resume.updated_at = datetime.utcnow()
    
    db.commit()

    # Return flat — same shape as the generate and edit endpoints.
    # Include the new filename so the frontend download button always fetches
    # the file that matches the current preview (not the pre-edit version).
    return {
        "preview_html": preview_html,
        "data": resume_data,
        "filename": safe_filename,
    }


@app.post("/api/resumes/{resume_id}/switch-template", tags=["Resume Editing"])
async def switch_resume_template(
    resume_id: int,
    template_id: str = Form(...),
    user_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
):
    """Re-render a resume with a different template without consuming any edit quota.

    Works for both guests (user_id omitted) and logged-in users.
    No OpenAI call is made — only the visual layout changes.
    """
    if user_id:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    else:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id.is_(None)).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not resume.resume_data:
        raise HTTPException(status_code=400, detail="Resume data not available")

    resolved_template = resolve_template_id(template_id)
    if resolved_template == "modern" and (template_id or "").strip().lower() != "modern":
        raise HTTPException(status_code=400, detail=f"Unknown template '{template_id}'")

    resume_data = json.loads(resume.resume_data)
    resume_builder = ResumeBuilder()
    resume_filename = f"resume_{uuid.uuid4().hex[:10]}.docx"
    safe_filename = sanitize_filename(resume_filename)
    resume_path = RESUMES_DIR / safe_filename
    resume_builder.build_word_document(str(resume_path), resume_data, template_id=resolved_template)
    preview_html = resume_builder.build_html_preview(resume_data, template_id=resolved_template)

    resume.preview_html = preview_html
    resume.file_path = str(resume_path)
    resume.template_id = resolved_template
    resume.updated_at = datetime.utcnow()
    db.commit()

    return {
        "status": "success",
        "preview_html": preview_html,
        "filename": safe_filename,
        "template_id": resolved_template,
    }


@app.get("/api/users/{user_id}/prompt-info", tags=["User"])
async def get_prompt_info(user_id: int, db: Session = Depends(get_db)):
    """Get user's prompt count and membership tier."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    max_prompts = get_max_prompts_for_tier(user.membership_tier)
    
    return {
        "prompt_count": user.prompt_count,
        "max_prompts": max_prompts,
        "membership_tier": user.membership_tier,
        "remaining_prompts": max(0, max_prompts - user.prompt_count),
    }


@app.get("/api/templates", tags=["Templates"])
async def get_templates():
    """Get available resume templates"""
    return {
        "status": "success",
        "templates": TEMPLATE_LIST,
    }


@app.get("/api/templates/previews", tags=["Templates"])
async def get_template_previews():
    """Return a pre-rendered dummy resume HTML string for each template.

    Used by the frontend template carousel so users can see a realistic
    full-resume preview before selecting a layout. No authentication required.
    """
    builder = ResumeBuilder()
    return {
        tmpl["id"]: builder.build_html_preview(DUMMY_CANDIDATE, tmpl["id"])
        for tmpl in TEMPLATE_LIST
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
