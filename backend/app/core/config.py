from decimal import Decimal
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

    # PayPal. mock never calls PayPal and needs no keys; sandbox and live do.
    PAYPAL_MODE: Literal["mock", "sandbox", "live"] = "mock"
    PAYPAL_CLIENT_ID: str | None = None
    PAYPAL_CLIENT_SECRET: str | None = None
    PAYPAL_WEBHOOK_ID: str | None = None
    PAYPAL_TIMEOUT_SECONDS: float = 15.0
    PAYPAL_MAX_RETRIES: int = 2

    # Spend caps for payouts, in the project currency.
    PAYOUT_MAX_PER_ACTION: Decimal = Decimal("10000.00")
    PAYOUT_MAX_PER_DAY: Decimal = Decimal("50000.00")

    LLM_MODE: str
    DEMO_MODE: bool
    JOBS_MODE: str

    @property
    def cors_origins(self) -> list[str]:
        return self._split(self.CORS_ORIGINS)

    @property
    def clerk_authorized_parties(self) -> list[str]:
        return self._split(self.CLERK_AUTHORIZED_PARTIES)

    @property
    def paypal_base_url(self) -> str:
        """Derived from the mode so a typo cannot point live mode at the sandbox."""
        if self.PAYPAL_MODE == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

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

        if self.PAYPAL_MODE == "mock":
            if self.APP_ENV == "production":
                raise ValueError("PAYPAL_MODE=mock is not allowed when APP_ENV=production.")
        elif self.PAYPAL_MODE == "live" and self.APP_ENV != "production":
            raise ValueError("PAYPAL_MODE=live is only allowed when APP_ENV=production.")
        elif not (self.PAYPAL_CLIENT_ID and self.PAYPAL_CLIENT_SECRET):
            raise ValueError(
                "PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are required "
                "when PAYPAL_MODE is not mock."
            )
        if self.PAYPAL_TIMEOUT_SECONDS <= 0:
            raise ValueError("PAYPAL_TIMEOUT_SECONDS must be greater than zero.")
        if self.PAYPAL_MAX_RETRIES < 0:
            raise ValueError("PAYPAL_MAX_RETRIES cannot be negative.")
        if self.PAYOUT_MAX_PER_ACTION <= 0 or self.PAYOUT_MAX_PER_DAY <= 0:
            raise ValueError("Payout spend caps must be greater than zero.")
        return self

    @staticmethod
    def _split(value: str | None) -> list[str]:
        return [item.strip() for item in (value or "").split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
