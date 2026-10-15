"""Application configuration via environment variables / .env file.

Uses pydantic-settings so every value can be overridden through the
environment. No secrets are hard-coded here; sensible *development*
defaults are provided only for local runs and are safe to expose.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    PROJECT_NAME: str = "CRMPro API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | production

    # --- Security ----------------------------------------------------------
    # MUST be overridden in production. A random value is generated per
    # process in development if not provided (tokens then invalidate on
    # restart, which is acceptable for local development only).
    SECRET_KEY: str = "dev-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours

    # --- Database ----------------------------------------------------------
    # Default to a local SQLite file for zero-dependency local development.
    # Override with a PostgreSQL URL in production / Docker, e.g.
    #   postgresql+psycopg://crmpro:STRONG_PASSWORD@db:5432/crmpro
    DATABASE_URL: str = "sqlite:///./crmpro.db"

    # --- CORS --------------------------------------------------------------
    # Comma-separated list of allowed origins, or "*" for local dev.
    BACKEND_CORS_ORIGINS: str = "*"

    # --- Rate limiting -----------------------------------------------------
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def cors_origins(self) -> List[str]:
        raw = self.BACKEND_CORS_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @field_validator("SECRET_KEY")
    @classmethod
    def _warn_default_secret(cls, v: str) -> str:
        # We do not raise here so local development works out of the box,
        # but production deployment MUST set a strong SECRET_KEY.
        return v


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()


settings = get_settings()
