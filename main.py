import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
from doc_builder import ResumeBuilder
from prompts import SYSTEM_PROMPT_DRAFT, create_resume_prompt
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

# Initialize database
init_db()

# Security
security = HTTPBearer()

# FastAPI app initialization
app = FastAPI(
    title="Resume Generator API",
    version="1.0.0",
    description="Production-ready FastAPI application for generating professional resumes"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File upload configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
RESUMES_DIR = Path(os.getenv("RESUMES_DIR", "./resumes"))
UPLOAD_DIR.mkdir(exist_ok=True)
RESUMES_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 52428800))

# Pydantic Models
class ContactInfo(BaseModel):
    email: EmailStr
    phone: str
    location: str

class ExperienceItem(BaseModel):
    title: str
    company: str
    location: str
    dates: str
    description: str
    bullets: List[str] = []

class EducationItem(BaseModel):
    degree: str
    institution: str
    field: str
    graduation_year: str

class CandidateInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    contact: ContactInfo
    professional_summary: str = Field(..., min_length=10, max_length=500)
    key_skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    additional_information: Optional[str] = None
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
        
        return {
            "status": "success",
            "message": "Login successful",
            "user_id": user.id,
            "token": str(user.id)  # Simplified - use JWT in production
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error logging in: {str(e)}")

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
        candidate_dict = candidate.dict(exclude={'user_id'})
        
        # Build Word document
        resume_builder = ResumeBuilder()
        resume_filename = f"resume_{uuid.uuid4().hex[:8]}_{candidate.name.replace(' ', '_')}.docx"
        resume_path = RESUMES_DIR / resume_filename
        
        resume_builder.build_word_document(str(resume_path), candidate_dict)
        
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
        
        # Save to database if user_id provided
        resume_id = None
        if user_id:
            resume_record = Resume(
                user_id=user_id,
                name=candidate.name,
                file_path=str(resume_path),
                professional_summary=enhanced_summary,
                skills=json.dumps(candidate.key_skills + candidate.technical_skills),
                experience=json.dumps([exp.dict() for exp in candidate.experience]),
                education=json.dumps([edu.dict() for edu in candidate.education]),
                contact_info=json.dumps(candidate.contact.dict())
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
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating resume: {str(e)}")

@app.get("/api/resumes", tags=["Resume Management"])
async def get_user_resumes(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all resumes for a user"""
    try:
        resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
        return {
            "status": "success",
            "resumes": [
                {
                    "id": r.id,
                    "name": r.name,
                    "created_at": r.created_at.isoformat(),
                    "file_path": r.file_path
                }
                for r in resumes
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching resumes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching resumes: {str(e)}")

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

@app.get("/api/templates", tags=["Templates"])
async def get_templates():
    """Get available resume templates"""
    return {
        "status": "success",
        "templates": [
            {"id": 1, "name": "Modern", "description": "Clean and modern design"},
            {"id": 2, "name": "Classic", "description": "Traditional professional format"},
            {"id": 3, "name": "Creative", "description": "Creative and colorful design"},
            {"id": 4, "name": "Minimal", "description": "Minimalist design"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
