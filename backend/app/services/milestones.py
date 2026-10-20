from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Invoice, Milestone, Project
from app.models.enums import ActionKind, MilestoneStatus
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.services import actions
from app.services.projects import get_project


async def list_milestones(
    session: AsyncSession, project_id: UUID, owner_id: UUID
) -> list[Milestone]:
    await get_project(session, project_id, owner_id)
    result = await session.scalars(
        select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.due_date)
    )
    return list(result)


async def get_milestone(session: AsyncSession, milestone_id: UUID, owner_id: UUID) -> Milestone:
    milestone = await session.scalar(
        select(Milestone)
        .join(Project)
        .where(Milestone.id == milestone_id, Project.owner_id == owner_id)
    )
    if milestone is None:
        raise NotFoundError("Milestone")
    return milestone


async def create_milestone(
    session: AsyncSession, project_id: UUID, owner_id: UUID, data: MilestoneCreate
) -> Milestone:
    await get_project(session, project_id, owner_id)
    milestone = Milestone(project_id=project_id, **data.model_dump())
    session.add(milestone)
    await session.flush()
    await _propose_invoice(session, milestone)
    await session.commit()
    await session.refresh(milestone)
    return milestone


async def update_milestone(
    session: AsyncSession, milestone: Milestone, data: MilestoneUpdate
) -> Milestone:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(milestone, field, value)
    await _propose_invoice(session, milestone)
    await session.commit()
    await session.refresh(milestone)
    return milestone


async def delete_milestone(session: AsyncSession, milestone: Milestone) -> None:
    await session.delete(milestone)
    await session.commit()


async def _propose_invoice(session: AsyncSession, milestone: Milestone) -> None:
    """Marking a milestone done puts an invoice proposal in the approval queue."""
    if milestone.status != MilestoneStatus.DONE:
        return
    existing = await session.scalar(
        select(Invoice).where(Invoice.milestone_id == milestone.id)
    )
    if existing is not None:
        return
    owner_id = await session.scalar(
        select(Project.owner_id).where(Project.id == milestone.project_id)
    )
    if owner_id is None:
        return
    await actions.propose(
        session,
        owner_id=owner_id,
        kind=ActionKind.CREATE_INVOICE,
        payload={"milestone_id": str(milestone.id)},
        rationale=f"'{milestone.title}' is done; bill the client for {milestone.amount}.",
        dedupe_key=f"invoice:{milestone.id}",
    )
