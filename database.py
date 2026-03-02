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
    # PostgreSQL (for Render) - requires SSL connection
    # Render's PostgreSQL requires SSL, but we can use sslmode=require
    # Add SSL configuration to connection string if not already present
    if "sslmode" not in SQLALCHEMY_DATABASE_URL:
        # Add sslmode=require to the connection string
        if "?" in SQLALCHEMY_DATABASE_URL:
            SQLALCHEMY_DATABASE_URL += "&sslmode=require"
        else:
            SQLALCHEMY_DATABASE_URL += "?sslmode=require"
    
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=300,    # Recycle connections after 5 minutes
        pool_size=5,         # Number of connections to maintain
        max_overflow=10,     # Maximum overflow connections
        pool_timeout=30,     # Timeout for getting connection from pool
        echo=False,          # Set to True for SQL query logging
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency to get database session with retry logic
def get_db():
    db = SessionLocal()
    try:
        # Test the connection first
        db.execute("SELECT 1")
        yield db
    except Exception as e:
        # If connection fails, close and retry once
        db.close()
        logger = __import__('logging').getLogger(__name__)
        logger.warning(f"Database connection failed, retrying: {e}")
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    finally:
        db.close()
