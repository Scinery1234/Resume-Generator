from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base

import os

# Database configuration
# For Render: Use DATABASE_URL if provided (PostgreSQL), otherwise SQLite for local dev
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Render provides PostgreSQL - replace postgres:// with postgresql:// for SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
else:
    # Local development - use SQLite
    SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

# Create engine with appropriate connect_args based on database type
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL (for Render)
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()  
    try:
        yield db
    finally:
        db.close()
