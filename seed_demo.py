"""
Seed script: creates a demo user with pre-filled profile data and a sample resume.

Usage:
    python3 seed_demo.py

Demo credentials:
    Email:    demo@example.com
    Password: demo1234
"""
import sys
import json
import hashlib
from datetime import datetime

sys.path.insert(0, ".")

from database import engine, SessionLocal, init_db
from models import Base, User, Resume

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo1234"
DEMO_NAME = "Alex Demo"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def main():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing:
            print(f"Demo user already exists (id={existing.id}). Skipping creation.")
            return

        skills = json.dumps([
            "Python", "JavaScript", "React", "FastAPI",
            "SQL", "REST APIs", "Git", "Docker",
        ])
        experience = json.dumps([
            {
                "company": "Acme Corp",
                "title": "Software Engineer",
                "start_date": "2021-06",
                "end_date": "Present",
                "description": (
                    "Built and maintained full-stack web applications using React "
                    "and FastAPI. Reduced page load time by 40% through code splitting "
                    "and caching optimisations."
                ),
            },
            {
                "company": "Startup Inc.",
                "title": "Junior Developer",
                "start_date": "2019-08",
                "end_date": "2021-05",
                "description": (
                    "Developed REST APIs and automated reporting pipelines. "
                    "Collaborated with the design team to ship three major product features."
                ),
            },
        ])
        education = json.dumps([
            {
                "institution": "State University",
                "degree": "B.S. Computer Science",
                "start_date": "2015-09",
                "end_date": "2019-05",
                "gpa": "3.8",
            }
        ])
        summary = (
            "Results-driven software engineer with 5+ years of experience building "
            "scalable web applications. Passionate about clean code, developer "
            "experience, and delivering user-friendly products."
        )

        user = User(
            name=DEMO_NAME,
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            professional_summary=summary,
            skills=skills,
            experience=experience,
            education=education,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()  # get user.id before commit

        contact_info = json.dumps({
            "name": DEMO_NAME,
            "email": DEMO_EMAIL,
            "phone": "555-0100",
            "location": "San Francisco, CA",
            "linkedin": "linkedin.com/in/alex-demo",
            "github": "github.com/alex-demo",
        })

        resume = Resume(
            user_id=user.id,
            name="Alex Demo – Software Engineer",
            professional_summary=summary,
            skills=skills,
            experience=experience,
            education=education,
            contact_info=contact_info,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(resume)
        db.commit()

        print("Demo user created successfully!")
        print(f"  ID:       {user.id}")
        print(f"  Name:     {DEMO_NAME}")
        print(f"  Email:    {DEMO_EMAIL}")
        print(f"  Password: {DEMO_PASSWORD}")
        print(f"  Resume:   '{resume.name}' (id={resume.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
