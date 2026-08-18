import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

class Settings(BaseSettings):
    PROJECT_ROOT: Path = PROJECT_ROOT
    APP_NAME: str = "Audio Summarizer"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Gemini API
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Storage Paths
    STORAGE_DIR: Path = PROJECT_ROOT / "storage"
    UPLOADS_DIR: Path = PROJECT_ROOT / "storage" / "uploads"
    TRANSCRIPTS_DIR: Path = PROJECT_ROOT / "storage" / "transcripts"
    SUMMARIES_DIR: Path = PROJECT_ROOT / "storage" / "summaries"
    DB_PATH: Path = PROJECT_ROOT / "storage" / "audio_summarizer.db"
    
    # Max file upload size (default 250MB)
    MAX_UPLOAD_SIZE_BYTES: int = 250 * 1024 * 1024
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
for path in [settings.STORAGE_DIR, settings.UPLOADS_DIR, settings.TRANSCRIPTS_DIR, settings.SUMMARIES_DIR]:
    path.mkdir(parents=True, exist_ok=True)
