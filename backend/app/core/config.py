from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    SENTRY_DSN: Optional[str] = None
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    DEBUG: bool = False
    APP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    NOTIFICATION_MODE: str = "log"
    EMAIL_PROVIDER_API_KEY: Optional[str] = None
    EMAIL_SENDER: str = "StatusForge <onboarding@resend.dev>"

    # Firebase backend variables
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CLIENT_EMAIL: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
