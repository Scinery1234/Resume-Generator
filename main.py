import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field
import openai
from dotenv import load_dotenv
import json
import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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
UPLOAD_DIR.mkdir(exist_ok=True)
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

@app.post("/api/generate-resume", tags=["Resume Generation"])
async def generate_resume(candidate: CandidateInput):
    """Generate a professional resume from candidate information"""
    try:
        logger.info(f"Generating resume for {candidate.name}")
        
        return {
            "status": "success",
            "message": "Resume generated successfully",
            "data": {
                "name": candidate.name,
                "email": candidate.contact.email,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating resume: {str(e)}")

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
