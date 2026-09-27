"""
Configuration Module
====================
Loads all environment variables using Pydantic Settings.
Every configurable value in the project flows through this file.
This means:
  - No hardcoded secrets anywhere in the codebase
  - Easy to switch between dev/staging/production
  - Type-safe configuration with validation
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Pydantic automatically reads from .env file and validates types.
    """

    # ── Project ──────────────────────────────────────────────
    PROJECT_NAME: str = "YouTube Intelligence Platform"
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = "INFO"

    # ── CORS ─────────────────────────────────────────────────
    # Comma-separated origins, e.g. "http://localhost:3000,https://myapp.com"
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ── Database (PostgreSQL) ────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/youtube_chatbot"

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT Authentication ───────────────────────────────────
    JWT_SECRET_KEY: str = "change-this-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours

    # ── Google Gemini ────────────────────────────────────────
    GOOGLE_API_KEY: str = ""

    # ── Gemini Model ─────────────────────────────────────────
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # ── Qdrant ───────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "youtube_transcripts"
    # Local embedded mode (no server needed) — set to a directory path
    QDRANT_PATH: str = "./qdrant_data"

    # ── Whisper ──────────────────────────────────────────────
    # Model sizes: tiny, base, small, medium, large
    # 'base' is a good balance of speed vs accuracy for CPU
    WHISPER_MODEL_SIZE: str = "base"

    # ── Retrieval ────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 20       # Candidates from hybrid search
    RERANK_TOP_K: int = 5           # Final chunks after reranking
    RRF_K: int = 60                 # RRF smoothing constant

    # ── Chunking ─────────────────────────────────────────────
    CHUNK_SIZE: int = 500           # Characters per chunk
    CHUNK_OVERLAP: int = 50         # Overlap between chunks

    # ── Rate Limiting ────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 30   # Max requests per window
    RATE_LIMIT_WINDOW: int = 60     # Window in seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance used throughout the application
settings = Settings()
