from uuid import UUID

from fastapi import APIRouter, status

from app.auth.deps import CurrentUser, SessionDep
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.schemas.response import ApiResponse, success
from app.services import projects as project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ApiResponse[list[ProjectRead]])
async def list_projects(user: CurrentUser, session: SessionDep) -> ApiResponse[list[ProjectRead]]:
    projects = await project_service.list_projects(session, user.id)
    return success([ProjectRead.model_validate(project) for project in projects])


@router.post("", response_model=ApiResponse[ProjectRead], status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, user: CurrentUser, session: SessionDep
) -> ApiResponse[ProjectRead]:
    project = await project_service.create_project(session, user.id, payload)
    return success(ProjectRead.model_validate(project))


@router.get("/{project_id}", response_model=ApiResponse[ProjectRead])
async def get_project(
    project_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[ProjectRead]:
    project = await project_service.get_project(session, project_id, user.id)
    return success(ProjectRead.model_validate(project))


@router.patch("/{project_id}", response_model=ApiResponse[ProjectRead])
async def update_project(
    project_id: UUID, payload: ProjectUpdate, user: CurrentUser, session: SessionDep
) -> ApiResponse[ProjectRead]:
    project = await project_service.get_project(session, project_id, user.id)
    updated = await project_service.update_project(session, project, payload)
    return success(ProjectRead.model_validate(updated))


@router.delete("/{project_id}", response_model=ApiResponse[None])
async def delete_project(
    project_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[None]:
    project = await project_service.get_project(session, project_id, user.id)
    await project_service.delete_project(session, project)
    return success()
