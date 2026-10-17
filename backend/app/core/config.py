from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All values come from the environment (.env); nothing is defaulted in code."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: Literal["development", "test", "production"]
    SECRET_KEY: str
    DATABASE_URL: str
    CORS_ORIGINS: str
    FRONTEND_URL: str

    AUTH_MODE: Literal["dev", "clerk"]
    DEV_USER_EMAIL: str | None = None
    CLERK_SECRET_KEY: str | None = None
    CLERK_JWT_KEY: str | None = None
    CLERK_AUTHORIZED_PARTIES: str | None = None

    LLM_MODE: str
    DEMO_MODE: bool
    JOBS_MODE: str

    @property
    def cors_origins(self) -> list[str]:
        return self._split(self.CORS_ORIGINS)

    @property
    def clerk_authorized_parties(self) -> list[str]:
        return self._split(self.CLERK_AUTHORIZED_PARTIES)

    @model_validator(mode="after")
    def _require_mode_configuration(self) -> Settings:
        if self.AUTH_MODE == "dev":
            if self.APP_ENV == "production":
                raise ValueError("AUTH_MODE=dev is not allowed when APP_ENV=production.")
            if not self.DEV_USER_EMAIL:
                raise ValueError("DEV_USER_EMAIL is required when AUTH_MODE=dev.")
        else:
            if not self.CLERK_SECRET_KEY:
                raise ValueError("CLERK_SECRET_KEY is required when AUTH_MODE=clerk.")
            if not self.CLERK_AUTHORIZED_PARTIES:
                raise ValueError("CLERK_AUTHORIZED_PARTIES is required when AUTH_MODE=clerk.")
        return self

    @staticmethod
    def _split(value: str | None) -> list[str]:
        return [item.strip() for item in (value or "").split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
