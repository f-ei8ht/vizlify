from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import sql_enum
from app.models import (
    Client,
    Milestone,
    PendingAction,
    Project,
    TeamMember,
    User,
    WebhookEvent,
)
from app.models.enums import ActionKind, ActionStatus, MilestoneStatus, ProjectStatus

_SPLIT = (Decimal("40.00"), Decimal("35.00"), Decimal("25.00"))


async def _make_owner(session: AsyncSession, email: str = "owner@example.com") -> User:
    user = User(email=email, password_hash="x", business_name="Studio")
    session.add(user)
    await session.flush()
    return user


async def _make_project(session: AsyncSession, owner: User) -> Project:
    client = Client(owner_id=owner.id, name="Acme", email="billing@acme.example")
    session.add(client)
    await session.flush()
    project = Project(owner_id=owner.id, client_id=client.id, name="Redesign")
    session.add(project)
    await session.flush()
    return project


def test_enum_persists_values_not_names() -> None:
    assert sql_enum(ProjectStatus).enums == ["active", "completed", "archived"]


async def test_project_defaults_to_active(db_session: AsyncSession) -> None:
    owner = await _make_owner(db_session)
    project = await _make_project(db_session, owner)

    assert project.status is ProjectStatus.ACTIVE
    assert project.currency == "USD"


async def test_money_round_trips_exactly(db_session: AsyncSession) -> None:
    owner = await _make_owner(db_session)
    project = await _make_project(db_session, owner)
    db_session.add(Milestone(project_id=project.id, title="Build", amount=Decimal("2500.00")))
    await db_session.commit()

    stored = await db_session.scalar(select(Milestone).where(Milestone.project_id == project.id))

    assert stored.amount == Decimal("2500.00")
    assert stored.status is MilestoneStatus.TODO


async def test_team_split_totals_one_hundred(db_session: AsyncSession) -> None:
    owner = await _make_owner(db_session)
    project = await _make_project(db_session, owner)
    db_session.add_all(
        TeamMember(
            project_id=project.id,
            name=f"Member {index}",
            paypal_email=f"member{index}@northwind.example",
            share_percent=share,
        )
        for index, share in enumerate(_SPLIT)
    )
    await db_session.commit()

    total = await db_session.scalar(
        select(func.sum(TeamMember.share_percent)).where(TeamMember.project_id == project.id)
    )

    assert Decimal(total) == Decimal("100.00")


async def test_pending_action_defaults_to_pending(db_session: AsyncSession) -> None:
    owner = await _make_owner(db_session)
    action = PendingAction(
        owner_id=owner.id,
        kind=ActionKind.CREATE_INVOICE,
        dedupe_key="invoice:milestone-1",
        payload={"amount": "2500.00"},
    )
    db_session.add(action)
    await db_session.commit()

    assert action.status is ActionStatus.PENDING


async def test_pending_action_dedupe_key_is_unique(db_session: AsyncSession) -> None:
    owner = await _make_owner(db_session)
    payload = {"amount": "2500.00"}
    db_session.add(
        PendingAction(
            owner_id=owner.id,
            kind=ActionKind.CREATE_INVOICE,
            dedupe_key="dup",
            payload=payload,
        )
    )
    await db_session.commit()

    db_session.add(
        PendingAction(
            owner_id=owner.id,
            kind=ActionKind.CREATE_INVOICE,
            dedupe_key="dup",
            payload=payload,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_webhook_events_dedupe_on_paypal_id(db_session: AsyncSession) -> None:
    db_session.add(WebhookEvent(id="WH-1", event_type="INVOICING.INVOICE.PAID", payload={}))
    await db_session.commit()

    db_session.add(WebhookEvent(id="WH-1", event_type="INVOICING.INVOICE.PAID", payload={}))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
