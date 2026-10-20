from uuid import UUID

from fastapi import APIRouter, status

from app.auth.deps import CurrentUser, SessionDep
from app.models.enums import ActionKind
from app.schemas.action import ActionRead
from app.schemas.payout import PayoutRead
from app.schemas.response import ApiResponse, success
from app.services import actions as action_service
from app.services import payouts as payout_service

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.get("", response_model=ApiResponse[list[PayoutRead]])
async def list_payouts(
    user: CurrentUser, session: SessionDep
) -> ApiResponse[list[PayoutRead]]:
    payouts = await payout_service.list_payouts(session, user.id)
    return success([PayoutRead.model_validate(item) for item in payouts])


@router.get("/{payout_id}", response_model=ApiResponse[PayoutRead])
async def get_payout(
    payout_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[PayoutRead]:
    payout = await payout_service.get_payout(session, payout_id, user.id)
    return success(PayoutRead.model_validate(payout))


@router.post(
    "/{payout_id}/execute",
    response_model=ApiResponse[ActionRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def propose_execution(
    payout_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[ActionRead]:
    payout = await payout_service.get_payout(session, payout_id, user.id)
    action = await action_service.propose(
        session,
        owner_id=user.id,
        kind=ActionKind.EXECUTE_PAYOUT,
        payload={"payout_id": str(payout.id)},
        rationale=f"Send {payout.total:.2f} {payout.currency} to the team.",
        dedupe_key=f"payout-execute:{payout.id}",
    )
    await session.commit()
    return success(ActionRead.model_validate(action))
