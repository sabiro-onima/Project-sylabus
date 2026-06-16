from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ─────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "production", "test"] = "development"
    APP_NAME: str = "Sylabus System"
    API_V1_STR: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_URL_SYNC: str = ""   # wypełniane automatycznie poniżej

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── MinIO ────────────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minio_admin"
    MINIO_ROOT_PASSWORD: str = "minio_password"
    MINIO_BUCKET_NAME: str = "sylabus-exports"
    MINIO_SECURE: bool = False

    # ── JWT ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── SSO ──────────────────────────────────────────────────────────────────
    SSO_ENABLED: bool = False
    SSO_CLIENT_ID: str = ""
    SSO_CLIENT_SECRET: str = ""
    SSO_AUTHORIZATION_URL: str = ""
    SSO_TOKEN_URL: str = ""
    SSO_USERINFO_URL: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def build_sync_url(cls, v: str, info) -> str:
        """asyncpg → psycopg2 dla Alembic (który jest synchroniczny)."""
        if not v:
            db_url = info.data.get("DATABASE_URL", "")
            return db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
