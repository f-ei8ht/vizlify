from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import verify_session
from app.auth.provisioning import MissingClaimError, upsert_user
from app.core.config import settings
from app.db.session import get_db
from app.models import User

SessionDep = Annotated[AsyncSession, Depends(get_db)]


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_dev_user(session: AsyncSession) -> User | None:
    return await session.scalar(select(User).where(User.email == settings.DEV_USER_EMAIL))


async def get_current_user(request: Request, session: SessionDep) -> User:
    if settings.AUTH_MODE == "dev":
        user = await get_dev_user(session)
        if user is None:
            raise _unauthorized("The demo workspace is not ready yet.")
        return user

    claims = await verify_session(request)
    if claims is None:
        raise _unauthorized("You are not signed in.")
    try:
        return await upsert_user(session, claims)
    except MissingClaimError as exc:
        raise _unauthorized("Your session is missing required account information.") from exc


CurrentUser = Annotated[User, Depends(get_current_user)]
