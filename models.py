from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime
import hashlib

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    professional_summary = Column(Text)
    skills = Column(Text)
    experience = Column(Text)
    education = Column(Text)
    membership_tier = Column(String, default='free')  # 'free', 'pro', 'enterprise'
    prompt_count = Column(Integer, default=0)  # Number of prompts used
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def hash_password(password: str) -> str:
        """Simple password hashing (in production, use bcrypt)"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        return self.password_hash == self.hash_password(password)

class Resume(Base):
    __tablename__ = 'resumes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Allow null for guest resumes
    name = Column(String, nullable=False)
    file_path = Column(String)
    professional_summary = Column(Text)
    skills = Column(Text)
    experience = Column(Text)
    education = Column(Text)
    contact_info = Column(Text)
    resume_data = Column(Text)  # JSON string of the resume data for editing
    preview_html = Column(Text)  # Store preview HTML for editing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
