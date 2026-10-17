from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models import Project, TeamMember
from app.schemas.team_member import TeamMemberCreate, TeamMemberUpdate
from app.services.projects import get_project

MAX_SHARE = Decimal("100.00")


async def list_team_members(
    session: AsyncSession, project_id: UUID, owner_id: UUID
) -> list[TeamMember]:
    await get_project(session, project_id, owner_id)
    result = await session.scalars(
        select(TeamMember).where(TeamMember.project_id == project_id).order_by(TeamMember.name)
    )
    return list(result)


async def get_team_member(session: AsyncSession, member_id: UUID, owner_id: UUID) -> TeamMember:
    member = await session.scalar(
        select(TeamMember)
        .join(Project)
        .where(TeamMember.id == member_id, Project.owner_id == owner_id)
    )
    if member is None:
        raise NotFoundError("Team member")
    return member


async def _allocated_share(
    session: AsyncSession, project_id: UUID, exclude_id: UUID | None = None
) -> Decimal:
    statement = select(func.coalesce(func.sum(TeamMember.share_percent), 0)).where(
        TeamMember.project_id == project_id
    )
    if exclude_id is not None:
        statement = statement.where(TeamMember.id != exclude_id)
    return Decimal(await session.scalar(statement))


async def create_team_member(
    session: AsyncSession, project_id: UUID, owner_id: UUID, data: TeamMemberCreate
) -> TeamMember:
    await get_project(session, project_id, owner_id)
    allocated = await _allocated_share(session, project_id)
    if allocated + data.share_percent > MAX_SHARE:
        raise ConflictError("Team shares cannot exceed 100%.")
    member = TeamMember(project_id=project_id, **data.model_dump())
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


async def update_team_member(
    session: AsyncSession, member: TeamMember, data: TeamMemberUpdate
) -> TeamMember:
    if data.share_percent is not None:
        allocated = await _allocated_share(session, member.project_id, exclude_id=member.id)
        if allocated + data.share_percent > MAX_SHARE:
            raise ConflictError("Team shares cannot exceed 100%.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    await session.commit()
    await session.refresh(member)
    return member


async def delete_team_member(session: AsyncSession, member: TeamMember) -> None:
    await session.delete(member)
    await session.commit()
