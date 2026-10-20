import json

from fastapi import APIRouter, Request

from app.auth.deps import SessionDep
from app.core.errors import AppError
from app.paypal.deps import PayPalDep
from app.schemas.response import ApiResponse, success
from app.services import webhooks as webhook_service

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/paypal", response_model=ApiResponse[dict[str, str]])
async def paypal_webhook(
    request: Request,
    session: SessionDep,
    paypal: PayPalDep,
) -> ApiResponse[dict[str, str]]:
    raw = await request.body()
    try:
        event = json.loads(raw)
    except ValueError as exc:
        raise AppError("Webhook body is not valid JSON.") from exc
    if not isinstance(event, dict):
        raise AppError("Webhook body must be a JSON object.")

    result = await webhook_service.process(
        session,
        paypal,
        headers=dict(request.headers),
        event=event,
    )
    return success({"status": result})
