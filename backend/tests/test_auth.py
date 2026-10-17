from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.provisioning import upsert_user
from app.core.config import Settings, settings
from app.models import User
from app.scripts.seed import seed

_REQUIRED = {
    "SECRET_KEY": "test-secret",
    "DATABASE_URL": "sqlite+aiosqlite://",
    "CORS_ORIGINS": "http://example.test",
    "FRONTEND_URL": "http://example.test",
    "LLM_MODE": "mock",
    "DEMO_MODE": False,
    "JOBS_MODE": "inline",
}


def _verify(claims: dict[str, Any] | None):
    async def verify(request: Any) -> dict[str, Any] | None:
        return claims

    return verify


def test_dev_auth_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **_REQUIRED,
            APP_ENV="production",
            AUTH_MODE="dev",
            DEV_USER_EMAIL="owner@example.test",
        )


def test_clerk_auth_requires_a_secret_key() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **_REQUIRED,
            APP_ENV="development",
            AUTH_MODE="clerk",
            CLERK_AUTHORIZED_PARTIES="http://example.test",
        )


def test_dev_auth_requires_a_dev_user_email() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **_REQUIRED, APP_ENV="development", AUTH_MODE="dev")


async def test_dev_mode_resolves_the_seeded_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await seed(db_session)

    response = await client.get("/me")

    assert response.status_code == 200
    assert response.json()["data"]["email"] == settings.DEV_USER_EMAIL


async def test_dev_mode_is_unauthorized_without_a_user(client: AsyncClient) -> None:
    response = await client.get("/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_clerk_mode_provisions_a_user_from_claims(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "clerk")
    monkeypatch.setattr(
        "app.auth.deps.verify_session",
        _verify({"sub": "user_123", "email": "owner@studio.dev"}),
    )

    response = await client.get("/me")

    assert response.status_code == 200
    assert response.json()["data"]["email"] == "owner@studio.dev"


async def test_clerk_mode_rejects_a_signed_out_request(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "clerk")
    monkeypatch.setattr("app.auth.deps.verify_session", _verify(None))

    response = await client.get("/me")

    assert response.status_code == 401


async def test_clerk_mode_rejects_a_session_without_an_email(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "clerk")
    monkeypatch.setattr("app.auth.deps.verify_session", _verify({"sub": "user_404"}))

    response = await client.get("/me")

    assert response.status_code == 401


async def test_upsert_links_an_existing_account_by_email(
    db_session: AsyncSession,
) -> None:
    existing = User(email="owner@studio.dev", business_name="Studio")
    db_session.add(existing)
    await db_session.commit()

    resolved = await upsert_user(db_session, {"sub": "user_9", "email": "owner@studio.dev"})

    assert resolved.id == existing.id
    assert resolved.clerk_user_id == "user_9"
