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

from database import get_db
from models import Resume, User
from doc_builder import build_resume
from prompts import SYSTEM_PROMPT_DRAFT, SYSTEM_PROMPT_JSON
from sqlalchemy.orm import Session

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
        "timestamp": datetime.now().isoformat()
    }

# Resume Generation Routes
@app.post("/api/v1/draft")
async def create_draft(candidate: CandidateInput, db: Session = Depends(get_db)):
    """
    Generate a draft resume text using OpenAI ChatCompletion API.
    
    Returns:
        - draft (str): Plain text resume draft
    """
    try:
        if not openai.api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured"
            )
        
        # Construct prompt with candidate information
        prompt = f"""
        Create a professional Australian resume draft for the following candidate:
        
        Name: {candidate.name}
        Email: {candidate.contact.email}
        Phone: {candidate.contact.phone}
        Location: {candidate.contact.location}
        
        Professional Summary: {candidate.professional_summary}
        
        Key Skills: {', '.join(candidate.key_skills)}
        
        Experience:
        {json.dumps([exp.dict() for exp in candidate.experience], indent=2)}
        
        Education:
        {json.dumps([edu.dict() for edu in candidate.education], indent=2)}
        
        Certifications: {', '.join(candidate.certifications)}
        Awards: {', '.join(candidate.awards)}
        Technical Skills: {', '.join(candidate.technical_skills)}
        
        Additional Information: {candidate.additional_information or 'None'}
        """
        
        logger.info(f"Generating draft for candidate: {candidate.name}")
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_DRAFT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        draft_text = response.choices[0].message.content
        logger.info(f"Successfully generated draft for {candidate.name}")
        
        return {
            "success": True,
            "name": candidate.name,
            "draft": draft_text
        }
    
    except openai.error.AuthenticationError:
        logger.error("OpenAI authentication failed")
        raise HTTPException(
            status_code=401,
            detail="OpenAI API authentication failed. Check your API key."
        )
    except openai.error.RateLimitError:
        logger.error("OpenAI rate limit exceeded")
        raise HTTPException(
            status_code=429,
            detail="OpenAI rate limit exceeded. Please try again later."
        )
    except Exception as e:
        logger.error(f"Error generating draft: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating draft: {str(e)}"
        )

@app.post("/api/v1/resume_json")
async def generate_resume_json(candidate: CandidateInput, db: Session = Depends(get_db)):
    """
    Generate structured JSON resume data using OpenAI with strict schema.
    """
    try:
        if not openai.api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured"
            )
        
        prompt = f"""
        Convert the following candidate information into a well-structured JSON resume.
        
        Candidate Information:
        Name: {candidate.name}
        Email: {candidate.contact.email}
        Phone: {candidate.contact.phone}
        Location: {candidate.contact.location}
        Professional Summary: {candidate.professional_summary}
        Key Skills: {', '.join(candidate.key_skills)}
        Experience: {json.dumps([exp.dict() for exp in candidate.experience], indent=2)}
        Education: {json.dumps([edu.dict() for edu in candidate.education], indent=2)}
        Certifications: {', '.join(candidate.certifications)}
        Awards: {', '.join(candidate.awards)}
        Technical Skills: {', '.join(candidate.technical_skills)}
        Additional Information: {candidate.additional_information or 'None'}
        
        Return ONLY valid JSON with no markdown, code blocks, or commentary.
        """
        
        logger.info(f"Generating JSON resume for candidate: {candidate.name}")
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_JSON},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.5
        )
        
        resume_json_text = response.choices[0].message.content
        
        # Parse and validate JSON
        try:
            resume_json = json.loads(resume_json_text)
            
            # Save to database
            db_resume = Resume(
                name=candidate.name,
                email=candidate.contact.email,
                phone=candidate.contact.phone,
                location=candidate.contact.location,
                professional_summary=candidate.professional_summary
            )
            db.add(db_resume)
            db.commit()
            db.refresh(db_resume)
            
            logger.info(f"Successfully generated JSON resume for {candidate.name}")
            return {
                "success": True,
                "resume_id": db_resume.id,
                "resume": resume_json
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to parse JSON response from OpenAI. Please try again."
            )
    
    except openai.error.AuthenticationError:
        logger.error("OpenAI authentication failed")
        raise HTTPException(
            status_code=401,
            detail="OpenAI API authentication failed"
        )
    except openai.error.RateLimitError:
        logger.error("OpenAI rate limit exceeded")
        raise HTTPException(
            status_code=429,
            detail="OpenAI rate limit exceeded"
        )
    except Exception as e:
        logger.error(f"Error generating JSON: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating JSON: {str(e)}"
        )

@app.post("/api/v1/docx")
async def generate_docx(resume_data: ResumeJSON, db: Session = Depends(get_db)):
    """
    Generate a formatted .docx file from structured resume JSON.
    """
    try:
        logger.info(f"Generating DOCX for candidate: {resume_data.name}")
        
        # Convert Pydantic model to dict
        resume_dict = resume_data.dict()
        
        # Build the resume document
        filename = build_resume(resume_dict)
        
        if not os.path.exists(filename):
            raise HTTPException(
                status_code=500,
                detail="Failed to generate resume file"
            )
        
        logger.info(f"Successfully generated DOCX: {filename}")
        
        return FileResponse(
            path=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{resume_data.name.replace(' ', '_')}_Resume.docx"
        )
    
    except Exception as e:
        logger.error(f"Error generating DOCX: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating DOCX: {str(e)}"
        )

# File Upload Routes
@app.post("/api/v1/uploads/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    resume_id: Optional[int] = None,
    db: Session = Depends(get_db)
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

@app.get("/api/v1/uploads/documents/{resume_id}")
async def list_resume_documents(resume_id: int, db: Session = Depends(get_db)):
    """
    List all documents associated with a resume
    """
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # List files in upload directory
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Resume Management Routes
@app.get("/api/v1/resumes/{resume_id}")
async def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a saved resume by ID
    """
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return {
            "id": resume.id,
            "name": resume.name,
            "email": resume.email,
            "phone": resume.phone,
            "location": resume.location,
            "created_at": resume.created_at.isoformat() if resume.created_at else None,
            "updated_at": resume.updated_at.isoformat() if resume.updated_at else None
        }
        
    except Exception as e:
        logger.error(f"Error retrieving resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/v1/resumes")
async def list_resumes(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    List all saved resumes with pagination
    """
    try:
        resumes = db.query(Resume).filter(Resume.is_deleted == False).offset(skip).limit(limit).all()
        total = db.query(Resume).filter(Resume.is_deleted == False).count()
        
        return {
            "resumes": [
                {
                    "id": r.id,
                    "name": r.name,
                    "email": r.email,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in resumes
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error listing resumes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/api/v1/resumes/{resume_id}")
async def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Delete a resume by ID (soft delete)
    """
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        resume.is_deleted = True
        db.commit()
        
        logger.info(f"Resume {resume_id} deleted successfully")
        return {"success": True, "message": "Resume deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
