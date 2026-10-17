from uuid import UUID

from fastapi import APIRouter, status

from app.auth.deps import CurrentUser, SessionDep
from app.schemas.milestone import MilestoneCreate, MilestoneRead, MilestoneUpdate
from app.schemas.response import ApiResponse, success
from app.services import milestones as milestone_service

router = APIRouter(tags=["milestones"])


@router.get("/projects/{project_id}/milestones", response_model=ApiResponse[list[MilestoneRead]])
async def list_milestones(
    project_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[list[MilestoneRead]]:
    milestones = await milestone_service.list_milestones(session, project_id, user.id)
    return success([MilestoneRead.model_validate(item) for item in milestones])


@router.post(
    "/projects/{project_id}/milestones",
    response_model=ApiResponse[MilestoneRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_milestone(
    project_id: UUID, payload: MilestoneCreate, user: CurrentUser, session: SessionDep
) -> ApiResponse[MilestoneRead]:
    milestone = await milestone_service.create_milestone(session, project_id, user.id, payload)
    return success(MilestoneRead.model_validate(milestone))


@router.get("/milestones/{milestone_id}", response_model=ApiResponse[MilestoneRead])
async def get_milestone(
    milestone_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[MilestoneRead]:
    milestone = await milestone_service.get_milestone(session, milestone_id, user.id)
    return success(MilestoneRead.model_validate(milestone))


@router.patch("/milestones/{milestone_id}", response_model=ApiResponse[MilestoneRead])
async def update_milestone(
    milestone_id: UUID, payload: MilestoneUpdate, user: CurrentUser, session: SessionDep
) -> ApiResponse[MilestoneRead]:
    milestone = await milestone_service.get_milestone(session, milestone_id, user.id)
    updated = await milestone_service.update_milestone(session, milestone, payload)
    return success(MilestoneRead.model_validate(updated))


@router.delete("/milestones/{milestone_id}", response_model=ApiResponse[None])
async def delete_milestone(
    milestone_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[None]:
    milestone = await milestone_service.get_milestone(session, milestone_id, user.id)
    await milestone_service.delete_milestone(session, milestone)
    return success()
