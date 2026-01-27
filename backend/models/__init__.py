"""
SQLAlchemy Models Package
Database models and connection management using SQLAlchemy
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI to get database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Call this at application startup if not using Alembic migrations.
    """
    from models.user import User
    from models.chat_history import ChatMessage
    from models.google_token import GoogleToken
    
    Base.metadata.create_all(bind=engine)


# Import models to make them accessible from package
from models.user import User
from models.chat_history import ChatMessage
from models.google_token import GoogleToken

__all__ = ["Base", "engine", "SessionLocal", "get_db", "init_db", "User", "ChatMessage", "GoogleToken"]
