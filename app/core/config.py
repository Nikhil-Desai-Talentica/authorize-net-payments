"""Application configuration"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Authorize.Net
    AUTHORIZE_NET_API_LOGIN_ID: str
    AUTHORIZE_NET_TRANSACTION_KEY: str
    AUTHORIZE_NET_ENVIRONMENT: str = "sandbox"
    AUTHORIZE_NET_WEBHOOK_SECRET: str

    # Application
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
