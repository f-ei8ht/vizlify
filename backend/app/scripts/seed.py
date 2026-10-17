import asyncio
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionFactory
from app.models import Client, Milestone, Project, TeamMember, User
from app.models.enums import MilestoneStatus, ProjectStatus
from app.scripts.demo_data import DemoAgency, load_demo_agency


def _build_owner(agency: DemoAgency) -> User:
    return User(
        email=settings.DEV_USER_EMAIL,
        business_name=agency.business_name,
        paypal_email=agency.paypal_email,
    )


def _build_project(owner: User, client: Client, agency: DemoAgency) -> Project:
    project = Project(
        owner_id=owner.id,
        client_id=client.id,
        name=agency.project.name,
        currency=agency.project.currency,
        status=ProjectStatus.ACTIVE,
    )
    today = date.today()
    for milestone in agency.project.milestones:
        project.milestones.append(
            Milestone(
                title=milestone.title,
                amount=milestone.amount,
                due_date=today + timedelta(days=milestone.due_in_days),
                status=MilestoneStatus.TODO,
            )
        )
    for member in agency.project.team:
        project.team_members.append(
            TeamMember(
                name=member.name,
                paypal_email=member.paypal_email,
                share_percent=member.share_percent,
            )
        )
    return project


async def seed(session: AsyncSession) -> bool:
    """Idempotently load the demo agency. Returns True if it created it."""
    existing = await session.scalar(select(User).where(User.email == settings.DEV_USER_EMAIL))
    if existing is not None:
        print(f"Demo agency already seeded ({settings.DEV_USER_EMAIL}); nothing to do.")
        return False

    agency = load_demo_agency()
    owner = _build_owner(agency)
    owner.clients = [
        Client(name=client.name, email=client.email, tone_preference=client.tone_preference)
        for client in agency.clients
    ]
    session.add(owner)
    await session.flush()

    billing_client = next(
        client for client in owner.clients if client.name == agency.project.client_name
    )
    session.add(_build_project(owner, billing_client, agency))
    await session.commit()

    print(f"Seeded {agency.business_name}.")
    print(f"  login: {settings.DEV_USER_EMAIL} (AUTH_MODE=dev)")
    return True


def main() -> None:
    async def run() -> None:
        async with SessionFactory() as session:
            await seed(session)

    asyncio.run(run())


if __name__ == "__main__":
    main()
