"""Configuration for Integration Bridge"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service info
    APP_NAME: str = "NXB Integration Bridge"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Connected services
    APP_API_URL: str = "http://localhost:3000"  # AI Publisher Pro
    CW_API_URL: str = "http://localhost:3002"   # Companion Writer

    # Redis (optional - for Pub/Sub)
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    API_KEY: str = ""  # Optional API key for authentication

    # Job settings
    JOB_CLEANUP_HOURS: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
