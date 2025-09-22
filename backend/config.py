"""
Configuration settings for the resume builder backend
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/resume_builder"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4"  # Will be updated to o3 when available
    
    # Storage
    storage_type: str = "local"  # local, s3, minio
    storage_path: str = "./storage"
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_endpoint: Optional[str] = None
    
    # LaTeX Compilation
    tectonic_path: str = "tectonic"  # Path to Tectonic binary
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    access_token_expire_minutes: int = 30
    
    # File Processing
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: list = [".pdf", ".docx", ".txt"]
    
    # OCR
    tesseract_path: str = "tesseract"
    
    class Config:
        env_file = ".env"

settings = Settings()
