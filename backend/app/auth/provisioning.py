from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class MissingClaimError(Exception):
    def __init__(self, claim: str) -> None:
        super().__init__(f"Session token is missing the '{claim}' claim")
        self.claim = claim


async def upsert_user(session: AsyncSession, claims: dict[str, Any]) -> User:
    clerk_user_id: str = claims["sub"]
    existing = await session.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if existing is not None:
        return existing

    email = claims.get("email")
    if not email:
        raise MissingClaimError("email")

    user = await session.scalar(select(User).where(User.email == email))
    if user is not None:
        user.clerk_user_id = clerk_user_id
    else:
        user = User(
            clerk_user_id=clerk_user_id,
            email=email,
            business_name=claims.get("business_name"),
        )
        session.add(user)

    await session.commit()
    await session.refresh(user)
    return user
