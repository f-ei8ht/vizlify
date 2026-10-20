"""The only path that is allowed to move money.

Approval calls this; the agent cannot. Every branch receives an already
approved `PendingAction` and returns a JSON-serialisable result.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import PendingAction
from app.models.enums import ActionKind
from app.paypal.client import PayPalClient
from app.services import invoicing, payouts


async def execute(
    session: AsyncSession, action: PendingAction, paypal: PayPalClient
) -> dict[str, Any]:
    kind = action.kind
    payload = action.payload

    if kind == ActionKind.CREATE_INVOICE:
        invoice = await invoicing.create_for_milestone(
            session,
            paypal,
            milestone_id=_uuid(payload, "milestone_id"),
            owner_id=action.owner_id,
        )
        return _invoice_result(invoice)

    if kind == ActionKind.SEND_INVOICE:
        invoice = await invoicing.send_existing(
            session,
            paypal,
            invoice_id=_uuid(payload, "invoice_id"),
            owner_id=action.owner_id,
        )
        return _invoice_result(invoice)

    if kind == ActionKind.SEND_REMINDER:
        invoice = await invoicing.send_reminder(
            session,
            paypal,
            invoice_id=_uuid(payload, "invoice_id"),
            owner_id=action.owner_id,
        )
        return _invoice_result(invoice)

    if kind == ActionKind.CANCEL_INVOICE:
        invoice = await invoicing.cancel(
            session,
            paypal,
            invoice_id=_uuid(payload, "invoice_id"),
            owner_id=action.owner_id,
        )
        return _invoice_result(invoice)

    if kind == ActionKind.PREPARE_PAYOUT:
        payout = await payouts.prepare_for_invoice(
            session,
            invoice_id=_uuid(payload, "invoice_id"),
            owner_id=action.owner_id,
        )
        return _payout_result(payout)

    if kind == ActionKind.EXECUTE_PAYOUT:
        payout = await payouts.execute_batch(
            session,
            paypal,
            payout_id=_uuid(payload, "payout_id"),
            owner_id=action.owner_id,
        )
        return _payout_result(payout)

    raise AppError("This kind of proposal is not implemented yet.")


def _uuid(payload: dict[str, Any], key: str) -> UUID:
    value = payload.get(key)
    if not isinstance(value, str):
        raise AppError(f"Proposal payload is missing '{key}'.")
    try:
        return UUID(value)
    except ValueError as exc:
        raise AppError(f"Proposal payload has an invalid '{key}'.") from exc


def _invoice_result(invoice: Any) -> dict[str, Any]:
    return {
        "invoice_id": str(invoice.id),
        "paypal_invoice_id": invoice.paypal_invoice_id,
        "number": invoice.number,
        "status": invoice.status.value,
        "amount": f"{invoice.amount:.2f}",
        "currency": invoice.currency,
    }


def _payout_result(payout: Any) -> dict[str, Any]:
    return {
        "payout_id": str(payout.id),
        "invoice_id": str(payout.invoice_id),
        "paypal_batch_id": payout.paypal_batch_id,
        "status": payout.status.value,
        "total": f"{payout.total:.2f}",
        "currency": payout.currency,
        "items": [
            {"id": str(item.id), "amount": f"{item.amount:.2f}", "status": item.status.value}
            for item in payout.items
        ],
    }
