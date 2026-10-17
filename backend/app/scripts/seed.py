import asyncio
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models import Client, Milestone, Project, TeamMember, User
from app.models.enums import MilestoneStatus, ProjectStatus, TonePreference

DEMO_EMAIL = "demo@vizlify.space"
DEMO_PASSWORD = "vizlify-demo"
DEMO_BUSINESS = "Northwind Studio"

_CLIENTS = (
    ("Acme Co", "billing@acme.example", TonePreference.FRIENDLY),
    ("Globex Corporation", "accounts@globex.example", TonePreference.FORMAL),
)

_MILESTONES = (
    ("Discovery & wireframes", Decimal("2500.00"), 14),
    ("Visual design", Decimal("4000.00"), 35),
    ("Build & launch", Decimal("6000.00"), 70),
)

_TEAM = (
    ("Rida Khan", "rida@northwind.example", Decimal("40.00")),
    ("Maya Patel", "maya@northwind.example", Decimal("35.00")),
    ("Sam Rivera", "sam@northwind.example", Decimal("25.00")),
)


async def _create_demo_agency(session: AsyncSession) -> User:
    owner = User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        business_name=DEMO_BUSINESS,
        paypal_email="northwind-facilitator@business.example",
    )
    session.add(owner)
    await session.flush()
    return owner


async def _create_clients(session: AsyncSession, owner: User) -> list[Client]:
    clients = [
        Client(owner_id=owner.id, name=name, email=email, tone_preference=tone)
        for name, email, tone in _CLIENTS
    ]
    session.add_all(clients)
    await session.flush()
    return clients


async def _create_project(session: AsyncSession, owner: User, client: Client) -> Project:
    project = Project(
        owner_id=owner.id,
        client_id=client.id,
        name="Acme website redesign",
        currency="USD",
        status=ProjectStatus.ACTIVE,
    )
    session.add(project)
    await session.flush()

    today = date.today()
    session.add_all(
        Milestone(
            project_id=project.id,
            title=title,
            amount=amount,
            due_date=today + timedelta(days=days),
            status=MilestoneStatus.TODO,
        )
        for title, amount, days in _MILESTONES
    )
    session.add_all(
        TeamMember(
            project_id=project.id,
            name=name,
            paypal_email=email,
            share_percent=share,
        )
        for name, email, share in _TEAM
    )
    return project


async def seed(session: AsyncSession) -> bool:
    """Idempotently load the demo agency. Returns True if it created it."""
    existing = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if existing is not None:
        print(f"Demo agency already seeded ({DEMO_EMAIL}); nothing to do.")
        return False

    owner = await _create_demo_agency(session)
    clients = await _create_clients(session, owner)
    await _create_project(session, owner, clients[0])
    await session.commit()

    print(f"Seeded {DEMO_BUSINESS}.")
    print(f"  login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"  clients: {len(_CLIENTS)}, milestones: {len(_MILESTONES)}, team: {len(_TEAM)}")
    return True


def main() -> None:
    async def run() -> None:
        async with SessionFactory() as session:
            await seed(session)

    asyncio.run(run())


if __name__ == "__main__":
    main()
