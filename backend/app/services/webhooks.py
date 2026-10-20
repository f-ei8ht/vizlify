"""PayPal webhook ingestion: verify, dedupe, then reconcile local state."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.models import (
    Invoice,
    Milestone,
    Payout,
    PayoutItem,
    Project,
    TeamMember,
    WebhookEvent,
)
from app.models.enums import (
    ActionKind,
    InvoiceStatus,
    PayoutItemStatus,
    PayoutStatus,
)
from app.paypal import webhooks as paypal_webhooks
from app.paypal.client import PayPalClient
from app.services import actions, audit

_INVOICE_STATUS = {
    "INVOICING.INVOICE.PAID": InvoiceStatus.PAID,
    "INVOICING.INVOICE.CANCELLED": InvoiceStatus.CANCELLED,
    "INVOICING.INVOICE.REFUNDED": InvoiceStatus.REFUNDED,
}

_BATCH_STATUS = {
    "PAYMENT.PAYOUTSBATCH.SUCCESS": PayoutStatus.SUCCESS,
    "PAYMENT.PAYOUTSBATCH.DENIED": PayoutStatus.DENIED,
    "PAYMENT.PAYOUTSBATCH.PROCESSING": PayoutStatus.PENDING,
    "PAYMENT.PAYOUTSBATCH.CANCELED": PayoutStatus.FAILED,
}

_ITEM_STATUS = {
    "PAYMENT.PAYOUTS-ITEM.SUCCEEDED": PayoutItemStatus.SUCCESS,
    "PAYMENT.PAYOUTS-ITEM.FAILED": PayoutItemStatus.FAILED,
    "PAYMENT.PAYOUTS-ITEM.DENIED": PayoutItemStatus.DENIED,
    "PAYMENT.PAYOUTS-ITEM.UNCLAIMED": PayoutItemStatus.UNCLAIMED,
    "PAYMENT.PAYOUTS-ITEM.BLOCKED": PayoutItemStatus.FAILED,
    "PAYMENT.PAYOUTS-ITEM.RETURNED": PayoutItemStatus.FAILED,
    "PAYMENT.PAYOUTS-ITEM.REFUNDED": PayoutItemStatus.FAILED,
    "PAYMENT.PAYOUTS-ITEM.CANCELED": PayoutItemStatus.FAILED,
    "PAYMENT.PAYOUTS-ITEM.HELD": PayoutItemStatus.PENDING,
}


async def process(
    session: AsyncSession,
    paypal: PayPalClient,
    *,
    headers: Mapping[str, str],
    event: dict[str, Any],
) -> str:
    if settings.PAYPAL_MODE != "mock":
        if not settings.PAYPAL_WEBHOOK_ID:
            raise AppError("PAYPAL_WEBHOOK_ID is not configured.")
        verified = await paypal_webhooks.verify_webhook(
            paypal,
            headers=headers,
            event=event,
            webhook_id=settings.PAYPAL_WEBHOOK_ID,
        )
        if not verified:
            raise AppError("Invalid PayPal webhook signature.")

    event_id = event.get("id")
    event_type = event.get("event_type")
    if not isinstance(event_id, str) or not event_id or not isinstance(event_type, str):
        raise AppError("Webhook payload is missing id or event_type.")

    record = await session.get(WebhookEvent, event_id)
    if record is not None and record.processed_at is not None:
        return "duplicate"
    if record is None:
        record = WebhookEvent(id=event_id, event_type=event_type, payload=event)
        session.add(record)
        await session.commit()
        record = await session.get(WebhookEvent, event_id)

    resource = event.get("resource")
    if not isinstance(resource, dict):
        raise AppError("Webhook payload has no resource.")

    if event_type in _INVOICE_STATUS:
        await _handle_invoice(session, event_type, resource)
    elif event_type in _BATCH_STATUS:
        await _handle_batch(session, event_type, resource)
    elif event_type in _ITEM_STATUS:
        await _handle_item(session, event_type, resource)

    record.processed_at = datetime.now(UTC)
    await audit.record(
        session,
        user_id=None,
        action="webhook_processed",
        entity="webhook_event",
        entity_id=event_id,
        data={"event_type": event_type},
    )
    await session.commit()
    return "processed"


async def _handle_invoice(
    session: AsyncSession, event_type: str, resource: dict[str, Any]
) -> None:
    paypal_id = resource.get("id")
    if not isinstance(paypal_id, str):
        return
    invoice = await session.scalar(
        select(Invoice).where(Invoice.paypal_invoice_id == paypal_id)
    )
    if invoice is None:
        return

    invoice.status = _INVOICE_STATUS[event_type]
    if invoice.status == InvoiceStatus.PAID:
        invoice.paid_at = datetime.now(UTC)
    await session.flush()

    if event_type == "INVOICING.INVOICE.PAID":
        owner_id = await _owner_for_invoice(session, invoice)
        if owner_id is None:
            return
        has_team = await session.scalar(
            select(TeamMember.id)
            .join(Project, TeamMember.project_id == Project.id)
            .join(Milestone, Milestone.project_id == Project.id)
            .where(Milestone.id == invoice.milestone_id)
            .limit(1)
        )
        if has_team is not None:
            await actions.propose(
                session,
                owner_id=owner_id,
                kind=ActionKind.PREPARE_PAYOUT,
                payload={"invoice_id": str(invoice.id)},
                rationale="The invoice was paid; prepare the team split for approval.",
                dedupe_key=f"payout:{invoice.id}",
            )


async def _handle_batch(
    session: AsyncSession, event_type: str, resource: dict[str, Any]
) -> None:
    batch_id = resource.get("payout_batch_id")
    if not isinstance(batch_id, str):
        header = resource.get("batch_header")
        if isinstance(header, dict):
            batch_id = header.get("payout_batch_id")
    if not isinstance(batch_id, str):
        return
    payout = await session.scalar(select(Payout).where(Payout.paypal_batch_id == batch_id))
    if payout is None:
        return
    payout.status = _BATCH_STATUS[event_type]
    await session.flush()


async def _handle_item(
    session: AsyncSession, event_type: str, resource: dict[str, Any]
) -> None:
    item = await _find_item(session, resource)
    if item is None:
        return
    paypal_item_id = resource.get("payout_item_id")
    if isinstance(paypal_item_id, str):
        item.paypal_item_id = paypal_item_id
    item.status = _ITEM_STATUS[event_type]
    await session.flush()


async def _find_item(session: AsyncSession, resource: dict[str, Any]) -> PayoutItem | None:
    paypal_item_id = resource.get("payout_item_id")
    if isinstance(paypal_item_id, str):
        item = await session.scalar(
            select(PayoutItem).where(PayoutItem.paypal_item_id == paypal_item_id)
        )
        if item is not None:
            return item

    details = resource.get("payout_item")
    sender_item_id = details.get("sender_item_id") if isinstance(details, dict) else None
    if isinstance(sender_item_id, str):
        try:
            item_id = UUID(sender_item_id)
        except ValueError:
            return None
        return await session.get(PayoutItem, item_id)
    return None


async def _owner_for_invoice(session: AsyncSession, invoice: Invoice) -> UUID | None:
    owner_id = await session.scalar(
        select(Project.owner_id)
        .join(Milestone, Milestone.project_id == Project.id)
        .where(Milestone.id == invoice.milestone_id)
    )
    return owner_id
