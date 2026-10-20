"""Team splits and PayPal payout batches.

Rounding is largest-remainder on integer cents, so the items always add up to
the exact amount being split and the result is deterministic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError
from app.models import Invoice, Milestone, Payout, PayoutItem, Project, TeamMember
from app.models.enums import InvoiceStatus, PayoutStatus
from app.paypal import payouts as paypal_payouts
from app.paypal.client import PayPalClient, new_request_id


def allocate_split(
    total: Decimal, members: list[TeamMember]
) -> list[tuple[TeamMember, Decimal]]:
    """Split `total` by share percent, with the agency keeping any remainder."""
    if not members:
        raise ConflictError("Add team members before preparing a payout.")
    total_share = sum((member.share_percent for member in members), Decimal("0"))
    if total_share > Decimal("100"):
        raise ConflictError("Team shares cannot exceed 100%.")

    total_cents = int((total * 100).to_integral_value(rounding=ROUND_HALF_UP))
    raw = [
        (member, Decimal(total_cents) * member.share_percent / Decimal("100"))
        for member in members
    ]
    target_cents = int(
        sum((value for _, value in raw), Decimal("0")).to_integral_value(rounding=ROUND_HALF_UP)
    )
    cents = [int(value) for _, value in raw]
    remaining = target_cents - sum(cents)

    order = sorted(
        range(len(members)),
        key=lambda index: (
            -(raw[index][1] - cents[index]),
            members[index].name,
            str(members[index].id),
        ),
    )
    for index in order[: max(remaining, 0)]:
        cents[index] += 1

    return [
        (members[index], (Decimal(cents[index]) / Decimal("100")).quantize(Decimal("0.01")))
        for index in range(len(members))
    ]


async def list_payouts(session: AsyncSession, owner_id: UUID) -> list[Payout]:
    result = await session.scalars(
        select(Payout)
        .join(Invoice, Payout.invoice_id == Invoice.id)
        .join(Milestone, Invoice.milestone_id == Milestone.id)
        .join(Project, Milestone.project_id == Project.id)
        .where(Project.owner_id == owner_id)
        .options(selectinload(Payout.items))
        .order_by(Payout.created_at.desc())
    )
    return list(result)


async def get_payout(session: AsyncSession, payout_id: UUID, owner_id: UUID) -> Payout:
    payout = await session.scalar(
        select(Payout)
        .join(Invoice, Payout.invoice_id == Invoice.id)
        .join(Milestone, Invoice.milestone_id == Milestone.id)
        .join(Project, Milestone.project_id == Project.id)
        .where(Payout.id == payout_id, Project.owner_id == owner_id)
        .options(selectinload(Payout.items))
    )
    if payout is None:
        raise NotFoundError("Payout")
    return payout


async def prepare_for_invoice(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    owner_id: UUID,
) -> Payout:
    invoice = await session.scalar(
        select(Invoice)
        .join(Milestone, Invoice.milestone_id == Milestone.id)
        .join(Project, Milestone.project_id == Project.id)
        .where(Invoice.id == invoice_id, Project.owner_id == owner_id)
    )
    if invoice is None:
        raise NotFoundError("Invoice")
    if invoice.status != InvoiceStatus.PAID:
        raise ConflictError("The invoice is not paid yet.")

    existing = await session.scalar(select(Payout).where(Payout.invoice_id == invoice.id))
    if existing is not None:
        return existing

    milestone = await session.get(Milestone, invoice.milestone_id)
    if milestone is None:
        raise NotFoundError("Milestone")
    members = list(
        await session.scalars(
            select(TeamMember)
            .where(TeamMember.project_id == milestone.project_id)
            .order_by(TeamMember.name)
        )
    )
    allocations = allocate_split(invoice.amount, members)
    total = sum((amount for _, amount in allocations), Decimal("0"))

    await _assert_within_caps(session, total)
    payout = Payout(
        invoice_id=invoice.id,
        status=PayoutStatus.PENDING,
        total=total,
        currency=invoice.currency,
    )
    payout.items = [
        PayoutItem(team_member_id=member.id, amount=amount) for member, amount in allocations
    ]
    session.add(payout)
    await session.flush()
    return payout


async def execute_batch(
    session: AsyncSession, paypal: PayPalClient, *, payout_id: UUID, owner_id: UUID
) -> Payout:
    payout = await get_payout(session, payout_id, owner_id)
    if payout.paypal_batch_id:
        return payout
    if not payout.items:
        raise ConflictError("This payout has no items.")
    if payout.total <= 0:
        raise ConflictError("This payout has no amount.")

    await _assert_within_caps(session, payout.total, exclude_id=payout.id)
    invoice = await session.get(Invoice, payout.invoice_id)
    items = []
    for item in payout.items:
        member = await session.get(TeamMember, item.team_member_id)
        if member is None:
            raise ConflictError("A payout item points at a missing team member.")
        items.append(
            {
                "recipient_type": "EMAIL",
                "amount": {"currency": payout.currency, "value": f"{item.amount:.2f}"},
                "receiver": member.paypal_email,
                "note": f"Share of invoice {invoice.number or invoice.id if invoice else ''}",
                "sender_item_id": str(item.id),
            }
        )

    payload = await paypal_payouts.create_payout_batch(
        paypal,
        sender_batch_id=f"vizlify-{payout.id}",
        currency=payout.currency,
        items=items,
        request_id=new_request_id("payout", payout.id),
    )
    batch_id = paypal_payouts.batch_id_from_response(payload)
    if not batch_id:
        raise ConflictError("PayPal returned no payout batch id.")
    payout.paypal_batch_id = batch_id
    payout.status = PayoutStatus.PENDING
    await session.flush()
    return payout


async def _assert_within_caps(
    session: AsyncSession, total: Decimal, *, exclude_id: UUID | None = None
) -> None:
    if total > settings.PAYOUT_MAX_PER_ACTION:
        raise ConflictError(
            f"Payout exceeds the per-action cap of {settings.PAYOUT_MAX_PER_ACTION:.2f}."
        )
    spent = await _spent_today(session, exclude_id=exclude_id)
    if spent + total > settings.PAYOUT_MAX_PER_DAY:
        raise ConflictError(
            f"Payout would exceed the daily cap of {settings.PAYOUT_MAX_PER_DAY:.2f}."
        )


async def _spent_today(session: AsyncSession, *, exclude_id: UUID | None = None) -> Decimal:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    statement = select(func.coalesce(func.sum(Payout.total), 0)).where(
        Payout.created_at >= start
    )
    if exclude_id is not None:
        statement = statement.where(Payout.id != exclude_id)
    value = await session.scalar(statement)
    return Decimal(str(value or 0))
