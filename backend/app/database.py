"""
Database configuration and session management for the GMAO application.
Uses PostgreSQL in production and SQLite during local development.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import Generator

# Database URL 
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./proact.db"  # Local fallback
)

# SQLite requires a specific connection argument
connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,        # Safely recycle DB connections
    echo=False                 # Set True only for debugging SQL
)

# Base class for models
class Base(DeclarativeBase):
    pass

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_db() -> Generator:
    """
    FastAPI dependency that provides a database session.
    Ensures proper cleanup after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all defined tables.
    Called during application startup.
    """
    import app.models  # Import all ORM models
    Base.metadata.create_all(bind=engine)
