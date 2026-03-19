"""
SQLAlchemy ORM models for the Resume Generator application.

Tables
------
users   — registered user accounts with profile and membership details
resumes — generated resume records linked to users (or stored as guest resumes)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime
import hashlib

Base = declarative_base()


class User(Base):
    """
    Represents a registered user account.

    Columns
    -------
    id                   : primary key
    name                 : display name entered at signup
    email                : unique login identifier
    password_hash        : SHA-256 hash of the user's password
    professional_summary : optional cached summary from the user's profile
    skills               : JSON-encoded list of skills (e.g. '["Python", "React"]')
    experience           : JSON-encoded list of work-experience objects
    education            : JSON-encoded list of education objects
    membership_tier      : 'free' | 'pro' | 'enterprise' — controls prompt limits
    prompt_count         : running count of AI editing prompts consumed
    created_at           : UTC timestamp when the account was created
    updated_at           : UTC timestamp of the last update (auto-updated by ORM)
    """

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # Optional cached profile fields (stored as JSON strings)
    professional_summary = Column(Text)
    skills = Column(Text)
    experience = Column(Text)
    education = Column(Text)

    # Membership / usage tracking
    membership_tier = Column(String, default='free')  # 'free', 'pro', 'enterprise'
    prompt_count = Column(Integer, default=0)         # Number of AI editing prompts used

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Return a SHA-256 hex digest of *password*.

        Note: SHA-256 is used here for simplicity. In a production system,
        replace this with bcrypt or Argon2 for proper password security.
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Return True if *password* matches the stored hash."""
        return self.password_hash == self.hash_password(password)


class Resume(Base):
    """
    Represents a generated resume record.

    A resume may belong to a logged-in user (user_id set) or be a guest
    resume created without an account (user_id is NULL).

    Columns
    -------
    id                   : primary key
    user_id              : foreign key to users.id; NULL for guest resumes
    name                 : human-readable resume title (typically the candidate's name)
    file_path            : absolute path to the generated .docx file on disk
    professional_summary : plain-text summary extracted from the resume data
    skills               : JSON-encoded list of skills
    experience           : JSON-encoded list of work-experience objects
    education            : JSON-encoded list of education objects
    contact_info         : JSON-encoded contact details (email, phone, location, linkedin)
    resume_data          : full JSON snapshot of the AI-generated resume — used for editing
    preview_html         : self-contained HTML string for the in-browser preview iframe
    created_at           : UTC timestamp when the resume was created
    updated_at           : UTC timestamp of the last update (auto-updated by ORM)
    """

    __tablename__ = 'resumes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # NULL = guest resume
    name = Column(String, nullable=False)
    file_path = Column(String)

    # Denormalised text fields mirroring the resume content for quick access
    professional_summary = Column(Text)
    skills = Column(Text)
    experience = Column(Text)
    education = Column(Text)
    contact_info = Column(Text)

    # Full JSON snapshot stored for AI-powered editing (POST /api/resumes/{id}/edit)
    resume_data = Column(Text)

    # Pre-rendered HTML stored to avoid rebuilding the preview on every request
    preview_html = Column(Text)

    # Template/layout used to render this resume (e.g. 'modern', 'classic')
    template_id = Column(String, default='modern')

    # Number of AI edits consumed by a guest (no account) on this resume
    guest_edit_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
