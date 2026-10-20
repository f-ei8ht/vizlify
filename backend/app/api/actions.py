from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import CurrentUser, SessionDep
from app.models.enums import ActionStatus
from app.paypal.deps import PayPalDep
from app.schemas.action import ActionRead, RejectRequest
from app.schemas.response import ApiResponse, success
from app.services import actions as action_service

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=ApiResponse[list[ActionRead]])
async def list_actions(
    user: CurrentUser,
    session: SessionDep,
    status: ActionStatus | None = None,
) -> ApiResponse[list[ActionRead]]:
    proposals = await action_service.list_actions(session, user.id, status=status)
    return success([ActionRead.model_validate(item) for item in proposals])


@router.get("/{action_id}", response_model=ApiResponse[ActionRead])
async def get_action(
    action_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[ActionRead]:
    action = await action_service.get_action(session, action_id, user.id)
    return success(ActionRead.model_validate(action))


@router.post("/{action_id}/approve", response_model=ApiResponse[ActionRead])
async def approve_action(
    action_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    paypal: PayPalDep,
) -> ApiResponse[ActionRead]:
    action = await action_service.get_action(
        session, action_id, user.id, for_update=True
    )
    approved = await action_service.approve(
        session, action, user_id=user.id, paypal=paypal
    )
    return success(ActionRead.model_validate(approved))


@router.post("/{action_id}/reject", response_model=ApiResponse[ActionRead])
async def reject_action(
    action_id: UUID,
    payload: RejectRequest,
    user: CurrentUser,
    session: SessionDep,
) -> ApiResponse[ActionRead]:
    action = await action_service.get_action(
        session, action_id, user.id, for_update=True
    )
    rejected = await action_service.reject(
        session, action, user_id=user.id, reason=payload.reason
    )
    return success(ActionRead.model_validate(rejected))
