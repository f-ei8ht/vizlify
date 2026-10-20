"""Proposals and the approval gate.

The agent (and the UI) may only create `PendingAction` rows. Approving one runs
the executor exactly once; a second approval is a conflict, never a second
payment.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models import PendingAction
from app.models.enums import ActionKind, ActionStatus
from app.paypal.client import PayPalClient
from app.services import audit
from app.services import executor as executor_service


async def propose(
    session: AsyncSession,
    *,
    owner_id: UUID,
    kind: ActionKind,
    payload: dict[str, Any],
    rationale: str,
    dedupe_key: str,
) -> PendingAction:
    existing = await session.scalar(
        select(PendingAction).where(PendingAction.dedupe_key == dedupe_key)
    )
    if existing is not None:
        return existing

    action = PendingAction(
        owner_id=owner_id,
        kind=kind,
        payload=payload,
        rationale=rationale,
        dedupe_key=dedupe_key,
        status=ActionStatus.PENDING,
    )
    session.add(action)
    await session.flush()
    await audit.record(
        session,
        user_id=owner_id,
        action="proposed",
        entity="pending_action",
        entity_id=action.id,
        data={"kind": kind.value, "dedupe_key": dedupe_key},
    )
    return action


async def list_actions(
    session: AsyncSession,
    owner_id: UUID,
    *,
    status: ActionStatus | None = None,
) -> list[PendingAction]:
    statement = (
        select(PendingAction)
        .where(PendingAction.owner_id == owner_id)
        .order_by(PendingAction.created_at.desc())
    )
    if status is not None:
        statement = statement.where(PendingAction.status == status)
    return list(await session.scalars(statement))


async def get_action(
    session: AsyncSession,
    action_id: UUID,
    owner_id: UUID,
    *,
    for_update: bool = False,
) -> PendingAction:
    statement = select(PendingAction).where(
        PendingAction.id == action_id, PendingAction.owner_id == owner_id
    )
    if for_update:
        statement = statement.with_for_update()
    action = await session.scalar(statement)
    if action is None:
        raise NotFoundError("Proposal")
    return action


async def approve(
    session: AsyncSession,
    action: PendingAction,
    *,
    user_id: UUID,
    paypal: PayPalClient,
) -> PendingAction:
    if action.status != ActionStatus.PENDING:
        raise ConflictError(f"This proposal is already {action.status.value}.")

    action_id = action.id
    try:
        result = await executor_service.execute(session, action, paypal)
        action.status = ActionStatus.EXECUTED
        action.result = result
        action.error = None
        await audit.record(
            session,
            user_id=user_id,
            action="approved",
            entity="pending_action",
            entity_id=action_id,
            data={"kind": action.kind.value},
        )
        await audit.record(
            session,
            user_id=user_id,
            action="executed",
            entity="pending_action",
            entity_id=action_id,
            data=result,
        )
        await session.commit()
        await session.refresh(action)
        return action
    except Exception as exc:
        await session.rollback()
        failed = await session.get(PendingAction, action_id)
        if failed is not None:
            failed.status = ActionStatus.FAILED
            failed.error = _safe_error(exc)
            await audit.record(
                session,
                user_id=user_id,
                action="execution_failed",
                entity="pending_action",
                entity_id=action_id,
                data={"error": _safe_error(exc)},
            )
            await session.commit()
        raise


async def reject(
    session: AsyncSession,
    action: PendingAction,
    *,
    user_id: UUID,
    reason: str,
) -> PendingAction:
    if action.status != ActionStatus.PENDING:
        raise ConflictError(f"This proposal is already {action.status.value}.")

    action.status = ActionStatus.REJECTED
    action.result = {"reason": reason}
    await audit.record(
        session,
        user_id=user_id,
        action="rejected",
        entity="pending_action",
        entity_id=action.id,
        data={"kind": action.kind.value, "reason": reason},
    )
    await session.commit()
    await session.refresh(action)
    return action


def _safe_error(exc: Exception) -> str:
    message = getattr(exc, "message", None)
    if isinstance(message, str) and message:
        return message
    return exc.__class__.__name__
