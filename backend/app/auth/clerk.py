from typing import Any

from clerk_backend_api.security import authenticate_request_async
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import Request

from app.core.config import settings


async def verify_session(request: Request) -> dict[str, Any] | None:
    options = AuthenticateRequestOptions(
        secret_key=settings.CLERK_SECRET_KEY,
        jwt_key=settings.CLERK_JWT_KEY,
        authorized_parties=settings.clerk_authorized_parties,
        accepts_token=["session_token"],
    )
    state = await authenticate_request_async(request, options)
    return state.payload if state.is_signed_in else None
