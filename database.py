"""
Database engine and session management for the Resume Generator application.

The database backend is chosen at runtime via the DATABASE_URL environment variable:
  - Not set   → SQLite file (./database.db) — suitable for local development
  - Set        → PostgreSQL (e.g. Render's managed database) — used in production

Usage
-----
Import `get_db` as a FastAPI dependency to obtain a per-request SQLAlchemy session::

    from database import get_db
    from sqlalchemy.orm import Session
    from fastapi import Depends

    @app.get("/example")
    def example(db: Session = Depends(get_db)):
        ...

Call `init_db()` once at application startup to create any missing tables.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base

import os

# ---------------------------------------------------------------------------
# Database URL resolution
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render (and some other hosts) provides the URL with the legacy "postgres://"
    # scheme; SQLAlchemy 1.4+ requires "postgresql://".
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
else:
    # Local development — use an SQLite file in the project root.
    SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

# ---------------------------------------------------------------------------
# Engine creation
# ---------------------------------------------------------------------------

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite requires check_same_thread=False when used with FastAPI's async
    # request handling, because requests may be served from different threads.
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL (production) — configure connection pooling and SSL.
    # Render's PostgreSQL instances require SSL; append sslmode=require if the
    # caller has not already included it in the connection string.
    if "sslmode" not in SQLALCHEMY_DATABASE_URL:
        separator = "&" if "?" in SQLALCHEMY_DATABASE_URL else "?"
        SQLALCHEMY_DATABASE_URL += f"{separator}sslmode=require"

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,   # Test each connection before using it (detects stale connections)
        pool_recycle=300,     # Recycle connections after 5 minutes to avoid server-side timeouts
        pool_size=5,          # Steady-state number of connections kept open
        max_overflow=10,      # Additional connections allowed above pool_size under load
        pool_timeout=30,      # Seconds to wait for a connection before raising an error
        echo=False,           # Set to True to log all generated SQL statements (debug only)
    )

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

# autocommit=False: transactions must be explicitly committed.
# autoflush=False:  changes are not automatically flushed to the DB before queries.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def init_db():
    """Create all tables defined in the ORM models if they do not already exist.

    This is idempotent — calling it multiple times is safe. It should be
    invoked once when the FastAPI application starts up.

    Also runs lightweight ALTER TABLE migrations for columns added after the
    initial schema (SQLAlchemy's create_all does not modify existing tables).
    """
    from sqlalchemy import text, inspect as sa_inspect

    Base.metadata.create_all(bind=engine)

    # Add guest_edit_count column to resumes if it was created before this
    # column was introduced (zero-downtime migration).
    with engine.connect() as conn:
        inspector = sa_inspect(engine)
        existing_cols = [c["name"] for c in inspector.get_columns("resumes")]
        if "guest_edit_count" not in existing_cols:
            conn.execute(text("ALTER TABLE resumes ADD COLUMN guest_edit_count INTEGER DEFAULT 0"))
            conn.commit()


def get_db():
    """FastAPI dependency that yields a database session for a single request.

    Yields a `Session` and ensures it is closed after the request completes,
    even if an exception is raised. If the initial connection fails, one retry
    is attempted before propagating the error.

    Example::

        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        # Verify the connection is alive before handing it to the route handler.
        db.execute("SELECT 1")
        yield db
    except Exception as e:
        # Connection failed — close the broken session and open a fresh one.
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
