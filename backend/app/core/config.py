from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    SENTRY_DSN: Optional[str] = None
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    DEBUG: bool = False
    APP_URL: str = "http://localhost:8000"
    NOTIFICATION_MODE: str = "log"
    EMAIL_PROVIDER_API_KEY: Optional[str] = None

    # Automatically reads from .env in the root directory
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()