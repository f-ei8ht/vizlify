from uuid import UUID

from fastapi import APIRouter, status

from app.auth.deps import CurrentUser, SessionDep
from app.schemas.response import ApiResponse, success
from app.schemas.team_member import TeamMemberCreate, TeamMemberRead, TeamMemberUpdate
from app.services import team as team_service

router = APIRouter(tags=["team"])


@router.get("/projects/{project_id}/team", response_model=ApiResponse[list[TeamMemberRead]])
async def list_team_members(
    project_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[list[TeamMemberRead]]:
    members = await team_service.list_team_members(session, project_id, user.id)
    return success([TeamMemberRead.model_validate(member) for member in members])


@router.post(
    "/projects/{project_id}/team",
    response_model=ApiResponse[TeamMemberRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_team_member(
    project_id: UUID, payload: TeamMemberCreate, user: CurrentUser, session: SessionDep
) -> ApiResponse[TeamMemberRead]:
    member = await team_service.create_team_member(session, project_id, user.id, payload)
    return success(TeamMemberRead.model_validate(member))


@router.patch("/team/{member_id}", response_model=ApiResponse[TeamMemberRead])
async def update_team_member(
    member_id: UUID, payload: TeamMemberUpdate, user: CurrentUser, session: SessionDep
) -> ApiResponse[TeamMemberRead]:
    member = await team_service.get_team_member(session, member_id, user.id)
    updated = await team_service.update_team_member(session, member, payload)
    return success(TeamMemberRead.model_validate(updated))


@router.delete("/team/{member_id}", response_model=ApiResponse[None])
async def delete_team_member(
    member_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[None]:
    member = await team_service.get_team_member(session, member_id, user.id)
    await team_service.delete_team_member(session, member)
    return success()
