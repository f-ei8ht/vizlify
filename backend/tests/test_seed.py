from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Client, Milestone, Project, TeamMember, User
from app.scripts.demo_data import load_demo_agency
from app.scripts.seed import seed


async def test_seed_creates_the_demo_agency(db_session: AsyncSession) -> None:
    created = await seed(db_session)

    assert created
    owner = await db_session.scalar(select(User).where(User.email == settings.DEV_USER_EMAIL))
    assert owner is not None
    assert await db_session.scalar(select(func.count()).select_from(Client)) == 2
    assert await db_session.scalar(select(func.count()).select_from(Project)) == 1
    assert await db_session.scalar(select(func.count()).select_from(Milestone)) == 3
    assert await db_session.scalar(select(func.count()).select_from(TeamMember)) == 3


async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    await seed(db_session)

    created_again = await seed(db_session)

    assert created_again is False
    assert await db_session.scalar(select(func.count()).select_from(User)) == 1


async def test_demo_team_split_totals_one_hundred(db_session: AsyncSession) -> None:
    await seed(db_session)

    total = await db_session.scalar(select(func.sum(TeamMember.share_percent)))

    assert Decimal(total) == Decimal("100.00")


def test_demo_agency_file_is_valid() -> None:
    agency = load_demo_agency()

    assert agency.clients
    assert sum((member.share_percent for member in agency.project.team), Decimal("0")) == Decimal(
        "100.00"
    )
