from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.clients import get_client


async def list_projects(session: AsyncSession, owner_id: UUID) -> list[Project]:
    result = await session.scalars(
        select(Project).where(Project.owner_id == owner_id).order_by(Project.name)
    )
    return list(result)


async def get_project(session: AsyncSession, project_id: UUID, owner_id: UUID) -> Project:
    project = await session.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    if project is None:
        raise NotFoundError("Project")
    return project


async def create_project(session: AsyncSession, owner_id: UUID, data: ProjectCreate) -> Project:
    await get_client(session, data.client_id, owner_id)
    project = Project(owner_id=owner_id, **data.model_dump())
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def update_project(session: AsyncSession, project: Project, data: ProjectUpdate) -> Project:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await session.commit()
    await session.refresh(project)
    return project


async def delete_project(session: AsyncSession, project: Project) -> None:
    await session.delete(project)
    await session.commit()
