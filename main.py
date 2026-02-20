from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging
import os
import openai

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for request validation
class ResumeRequest(BaseModel):
    data: str = Field(..., example="Your resume draft text goes here")

class ResumeResponse(BaseModel):
    resume_json: dict
    docx_url: str

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Main endpoints
@app.post("/draft", response_model=ResumeResponse)
async def create_draft(resume_request: ResumeRequest):
    try:
        # Placeholder for draft creation logic
        logger.info("Creating draft...")
        # Simulate OpenAI API call
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=[{"role": "user", "content": resume_request.data}]
        )
        resume_json = response['choices'][0]['message']['content']
        return ResumeResponse(resume_json=resume_json, docx_url="https://example.com/resume.docx")
    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/resume_json", response_model=ResumeResponse)
async def get_resume_json(resume_request: ResumeRequest):
    try:
        logger.info("Generating resume JSON...")
        resume_json = {"data": resume_request.data}
        return ResumeResponse(resume_json=resume_json, docx_url="https://example.com/resume.docx")
    except Exception as e:
        logger.error(f"Error generating resume JSON: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/docx", response_model=ResumeResponse)
async def create_docx(resume_request: ResumeRequest):
    try:
        logger.info("Generating DOCX...")
        return ResumeResponse(resume_json={}, docx_url="https://example.com/resume.docx")
    except Exception as e:
        logger.error(f"Error generating DOCX: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
