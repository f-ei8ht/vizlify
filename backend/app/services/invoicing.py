"""Invoice lifecycle: create a PayPal draft, send it, remind, cancel, sync."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models import Client, Invoice, Milestone, Project, User
from app.models.enums import InvoiceStatus, MilestoneStatus, TonePreference
from app.paypal import invoicing as paypal_invoicing
from app.paypal.client import PayPalClient, new_request_id

_STATUS_BY_PAYPAL = {
    "DRAFT": InvoiceStatus.DRAFT,
    "SENT": InvoiceStatus.SENT,
    "UNPAID": InvoiceStatus.SENT,
    "VIEWED": InvoiceStatus.SENT,
    "PAID": InvoiceStatus.PAID,
    "MARKED_AS_PAID": InvoiceStatus.PAID,
    "PARTIALLY_PAID": InvoiceStatus.PARTIALLY_PAID,
    "CANCELLED": InvoiceStatus.CANCELLED,
    "REFUNDED": InvoiceStatus.REFUNDED,
    "PARTIALLY_REFUNDED": InvoiceStatus.REFUNDED,
}

_TONE_COPY: dict[TonePreference, tuple[str, str]] = {
    TonePreference.FRIENDLY: (
        "A friendly reminder about invoice {number}",
        "Hi! Just a gentle reminder that invoice {number} for {amount} is due {due}. "
        "No stress if it is already on its way.",
    ),
    TonePreference.FORMAL: (
        "Payment reminder: invoice {number}",
        "This is a reminder that invoice {number} for {amount} is due on {due}. "
        "Please arrange payment at your earliest convenience.",
    ),
    TonePreference.FIRM: (
        "Overdue payment: invoice {number}",
        "Invoice {number} for {amount} was due on {due} and remains unpaid. "
        "Please settle it promptly or reply if there is an issue.",
    ),
}


async def list_invoices(session: AsyncSession, owner_id: UUID) -> list[Invoice]:
    result = await session.scalars(
        select(Invoice)
        .join(Milestone, Invoice.milestone_id == Milestone.id)
        .join(Project, Milestone.project_id == Project.id)
        .where(Project.owner_id == owner_id)
        .order_by(Invoice.created_at.desc())
    )
    return list(result)


async def get_invoice(session: AsyncSession, invoice_id: UUID, owner_id: UUID) -> Invoice:
    invoice = await session.scalar(
        select(Invoice)
        .join(Milestone, Invoice.milestone_id == Milestone.id)
        .join(Project, Milestone.project_id == Project.id)
        .where(Invoice.id == invoice_id, Project.owner_id == owner_id)
    )
    if invoice is None:
        raise NotFoundError("Invoice")
    return invoice


async def get_invoice_by_paypal_id(session: AsyncSession, paypal_invoice_id: str) -> Invoice | None:
    return await session.scalar(
        select(Invoice).where(Invoice.paypal_invoice_id == paypal_invoice_id)
    )


async def create_for_milestone(
    session: AsyncSession,
    paypal: PayPalClient,
    *,
    milestone_id: UUID,
    owner_id: UUID,
) -> Invoice:
    milestone = await session.scalar(
        select(Milestone)
        .join(Project, Milestone.project_id == Project.id)
        .where(Milestone.id == milestone_id, Project.owner_id == owner_id)
    )
    if milestone is None:
        raise NotFoundError("Milestone")

    existing = await session.scalar(
        select(Invoice).where(Invoice.milestone_id == milestone.id)
    )
    if existing is not None:
        if existing.status == InvoiceStatus.DRAFT and existing.paypal_invoice_id:
            await _send(session, paypal, existing)
        return existing

    if milestone.status == MilestoneStatus.BILLED:
        raise ConflictError("This milestone is already billed.")

    project = await session.get(Project, milestone.project_id)
    owner = await session.get(User, owner_id)
    if project is None or owner is None:
        raise NotFoundError("Project")
    client = await session.get(Client, project.client_id)
    if client is None:
        raise NotFoundError("Client")
    if not owner.paypal_email:
        raise ConflictError("Set your PayPal email before creating an invoice.")

    number = await paypal_invoicing.generate_invoice_number(paypal)
    paypal_id, _ = await paypal_invoicing.create_draft_invoice(
        paypal,
        invoice_number=number,
        currency=project.currency,
        invoicer_email=owner.paypal_email,
        recipient_email=client.email,
        item_name=milestone.title,
        amount=milestone.amount,
        note=f"{project.name} · {milestone.title}",
        request_id=new_request_id("invoice", milestone.id),
    )

    invoice = Invoice(
        milestone_id=milestone.id,
        paypal_invoice_id=paypal_id,
        number=number,
        amount=milestone.amount,
        currency=project.currency,
        status=InvoiceStatus.DRAFT,
        due_date=milestone.due_date,
    )
    session.add(invoice)
    await session.flush()

    await _send(session, paypal, invoice)
    return invoice


async def send_existing(
    session: AsyncSession, paypal: PayPalClient, *, invoice_id: UUID, owner_id: UUID
) -> Invoice:
    invoice = await get_invoice(session, invoice_id, owner_id)
    if invoice.status in {InvoiceStatus.PAID, InvoiceStatus.CANCELLED}:
        raise ConflictError(f"Invoice is already {invoice.status.value}.")
    await _send(session, paypal, invoice)
    return invoice


async def send_reminder(
    session: AsyncSession,
    paypal: PayPalClient,
    *,
    invoice_id: UUID,
    owner_id: UUID,
) -> Invoice:
    invoice = await get_invoice(session, invoice_id, owner_id)
    if not invoice.paypal_invoice_id:
        raise ConflictError("Invoice has no PayPal id yet.")
    if invoice.status in {InvoiceStatus.PAID, InvoiceStatus.CANCELLED}:
        raise ConflictError(f"Invoice is already {invoice.status.value}.")

    client = await _client_for_invoice(session, invoice)
    tone = client.tone_preference if client else TonePreference.FRIENDLY
    subject_template, body_template = _TONE_COPY[tone]
    subject = subject_template.format(number=invoice.number or invoice.id)
    note = body_template.format(
        number=invoice.number or invoice.id,
        amount=_money(invoice.amount, invoice.currency),
        due=invoice.due_date.isoformat() if invoice.due_date else "soon",
    )
    await paypal_invoicing.remind_invoice(
        paypal,
        invoice.paypal_invoice_id,
        subject=subject,
        note=note,
        request_id=new_request_id("reminder", invoice.id),
    )
    return invoice


async def cancel(
    session: AsyncSession, paypal: PayPalClient, *, invoice_id: UUID, owner_id: UUID
) -> Invoice:
    invoice = await get_invoice(session, invoice_id, owner_id)
    if invoice.status == InvoiceStatus.CANCELLED:
        return invoice
    if not invoice.paypal_invoice_id:
        raise ConflictError("Invoice has no PayPal id yet.")
    await paypal_invoicing.cancel_invoice(
        paypal,
        invoice.paypal_invoice_id,
        subject=f"Cancel invoice {invoice.number or invoice.id}",
        note="This invoice has been cancelled by the agency.",
        request_id=new_request_id("invoice-cancel", invoice.id),
    )
    invoice.status = InvoiceStatus.CANCELLED
    await session.flush()
    return invoice


async def sync_from_paypal(
    session: AsyncSession,
    paypal: PayPalClient,
    *,
    invoice_id: UUID,
    owner_id: UUID,
) -> Invoice:
    invoice = await get_invoice(session, invoice_id, owner_id)
    if not invoice.paypal_invoice_id:
        return invoice
    payload = await paypal_invoicing.get_invoice(paypal, invoice.paypal_invoice_id)
    status = payload.get("status")
    if isinstance(status, str) and status.upper() in _STATUS_BY_PAYPAL:
        invoice.status = _STATUS_BY_PAYPAL[status.upper()]
        if invoice.status == InvoiceStatus.PAID and invoice.paid_at is None:
            invoice.paid_at = datetime.now(UTC)
    await session.flush()
    return invoice


async def _send(session: AsyncSession, paypal: PayPalClient, invoice: Invoice) -> None:
    if not invoice.paypal_invoice_id:
        raise ConflictError("Invoice has no PayPal id yet.")
    await paypal_invoicing.send_invoice(
        paypal,
        invoice.paypal_invoice_id,
        request_id=new_request_id("invoice-send", invoice.id),
    )
    invoice.status = InvoiceStatus.SENT
    milestone = await session.get(Milestone, invoice.milestone_id)
    if milestone is not None:
        milestone.status = MilestoneStatus.BILLED
    await session.flush()


async def _client_for_invoice(session: AsyncSession, invoice: Invoice) -> Client | None:
    milestone = await session.get(Milestone, invoice.milestone_id)
    if milestone is None:
        return None
    project = await session.get(Project, milestone.project_id)
    if project is None:
        return None
    return await session.get(Client, project.client_id)


def _money(amount: Decimal, currency: str) -> str:
    return f"{amount:.2f} {currency}"
