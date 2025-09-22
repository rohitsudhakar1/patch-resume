"""
Database configuration and models
"""
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from typing import Generator

from .config import settings

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner = Column(String, nullable=False)
    resume_tex = Column(Text, nullable=False)
    compile_status = Column(String, default="pending")  # pending, success, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    outline = Column(JSON)  # For storing document outline/structure

class PendingPatch(Base):
    __tablename__ = "pending_patches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, default="proposed")  # proposed, discarded, applied
    created_at = Column(DateTime, default=datetime.utcnow)

class Change(Base):
    __tablename__ = "changes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patch_id = Column(UUID(as_uuid=True), nullable=False)
    type = Column(String, nullable=False)  # addition, removal
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    accepted = Column(Boolean, nullable=True)  # null = pending, true = accepted, false = rejected
    pdf_regions = Column(JSON)  # For storing PDF overlay regions

class UndoBuffer(Base):
    __tablename__ = "undo_buffer"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    resume_tex_snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database dependency
async def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database
async def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
