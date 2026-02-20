import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
import openai
from dotenv import load_dotenv
import json
import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime

# Try to import database modules, but don't fail if they're missing
try:
    from database import get_db
    from models import Resume, User
    from doc_builder import build_resume
    from prompts import SYSTEM_PROMPT_DRAFT, SYSTEM_PROMPT_JSON
    from sqlalchemy.orm import Session
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"Database modules not available: {e}")
    DATABASE_AVAILABLE = False
    
    # Create dummy function for get_db
    def get_db():
        yield None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    logger.warning("OPENAI_API_KEY not configured - draft/JSON generation will fail")

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
MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 52428800))  # 50MB

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

class ResumeJSON(BaseModel):
    name: str
    contact: ContactInfo
    professional_summary: str
    key_skills: List[str]
    experience: List[ExperienceItem]
    education: List[EducationItem]
    certifications: List[str]
    awards: List[str]
    technical_skills: List[str]
    additional_information: Optional[str]

# Root and Health Check Routes
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Resume Generator API",
        "version": "1.0.0",
        "database_available": DATABASE_AVAILABLE,
        "endpoints": {
            "health": "/health",
            "draft": "/api/v1/draft",
            "resume_json": "/api/v1/resume_json",
            "docx": "/api/v1/docx",
            "upload": "/api/v1/uploads/upload",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "openai_configured": bool(openai.api_key),
        "database_available": DATABASE_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

# File Upload Routes (doesn't require database)
@app.post("/api/v1/uploads/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    resume_id: Optional[int] = None,
    db = Depends(get_db)
):
    """
    Upload up to 10 documents for resume building
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        if len(files) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 files allowed per upload"
            )
        
        uploaded_files = []
        errors = []
        
        for file in files:
            try:
                # Validate file extension
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in ALLOWED_EXTENSIONS:
                    errors.append({
                        "filename": file.filename,
                        "error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                    })
                    continue
                
                # Validate file size
                file_content = await file.read()
                if len(file_content) > MAX_FILE_SIZE:
                    errors.append({
                        "filename": file.filename,
                        "error": f"File size exceeds maximum of {MAX_FILE_SIZE / 1024 / 1024}MB"
                    })
                    continue
                
                # Reset file pointer
                await file.seek(0)
                
                # Create unique filename
                timestamp = int(datetime.now().timestamp() * 1000)
                safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
                file_path = UPLOAD_DIR / safe_filename
                
                # Save file
                with open(file_path, "wb") as f:
                    f.write(file_content)
                
                uploaded_files.append({
                    "original_name": file.filename,
                    "saved_name": safe_filename,
                    "file_path": str(file_path),
                    "size": len(file_content),
                    "uploaded_at": datetime.now().isoformat()
                })
                
                logger.info(f"File uploaded successfully: {safe_filename}")
                
            except Exception as e:
                logger.error(f"Error uploading file {file.filename}: {str(e)}")
                errors.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        if not uploaded_files and errors:
            raise HTTPException(
                status_code=400,
                detail=f"All files failed to upload"
            )
        
        return {
            "success": True,
            "uploaded_files": uploaded_files,
            "errors": errors if errors else [],
            "resume_id": resume_id,
            "total_uploaded": len(uploaded_files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/v1/uploads/document/{filename}")
async def download_document(filename: str):
    """
    Download a previously uploaded document
    """
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Security: ensure file is within upload directory
        if not str(file_path.resolve()).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(
            path=file_path,
            media_type="application/octet-stream",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.delete("/api/v1/uploads/document/{filename}")
async def delete_document(filename: str):
    """
    Delete an uploaded document
    """
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Only allow deletion of files in upload directory
        if not str(file_path.resolve()).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        file_path.unlink()
        logger.info(f"File deleted: {filename}")
        
        return {"success": True, "message": f"File {filename} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

# Placeholder endpoints for database-dependent routes
@app.post("/api/v1/draft")
async def create_draft(candidate: CandidateInput):
    """Placeholder - requires database setup"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Contact administrator."
        )
    raise HTTPException(status_code=501, detail="Not implemented")

@app.post("/api/v1/resume_json")
async def generate_resume_json(candidate: CandidateInput):
    """Placeholder - requires database setup"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Contact administrator."
        )
    raise HTTPException(status_code=501, detail="Not implemented")

@app.post("/api/v1/docx")
async def generate_docx(resume_data: ResumeJSON):
    """Placeholder - requires database setup"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Contact administrator."
        )
    raise HTTPException(status_code=501, detail="Not implemented")

@app.get("/api/v1/resumes/{resume_id}")
async def get_resume(resume_id: int):
    """Placeholder - requires database setup"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Contact administrator."
        )
    raise HTTPException(status_code=501, detail="Not implemented")

@app.get("/api/v1/resumes")
async def list_resumes(skip: int = 0, limit: int = 10):
    """Placeholder - requires database setup"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Contact administrator."
        )
    raise HTTPException(status_code=501, detail="Not implemented")

@app.delete("/api/v1/resumes/{resume_id}")
async def delete_resume(resume_id: int):
    """Placeholder - requires database setup"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Contact administrator."
        )
    raise HTTPException(status_code=501, detail="Not implemented")

@app.get("/api/v1/uploads/documents/{resume_id}")
async def list_resume_documents(resume_id: int):
    """List uploaded documents"""
    documents = []
    if UPLOAD_DIR.exists():
        for file in sorted(UPLOAD_DIR.iterdir(), reverse=True):
            if file.is_file():
                documents.append({
                    "filename": file.name,
                    "size": file.stat().st_size,
                    "created_at": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
    
    return {
        "resume_id": resume_id,
        "documents": documents,
        "total_documents": len(documents)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
