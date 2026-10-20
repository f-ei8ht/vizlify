"""Append-only audit entries. Callers own the transaction."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def record(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    entity: str,
    entity_id: str | UUID | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            data=data,
        )
    )
    await session.flush()
