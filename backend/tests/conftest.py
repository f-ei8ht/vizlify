from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401  # registers tables on Base.metadata
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.paypal import build_mock_transport
from app.paypal.client import PayPalClient, PayPalConfig
from app.paypal.deps import get_paypal
from app.scripts.seed import seed


@pytest.fixture(autouse=True)
def _local_auth_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "dev")


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def paypal_client() -> AsyncIterator[PayPalClient]:
    client = PayPalClient(PayPalConfig.mock(), transport=build_mock_transport())
    yield client
    await client.aclose()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    paypal_client: PayPalClient,
) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_paypal] = lambda: paypal_client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def seeded_client(
    client: AsyncClient, db_session: AsyncSession
) -> AsyncIterator[AsyncClient]:
    await seed(db_session)
    yield client
