from datetime import date
from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.auth.deps import CurrentUser, SessionDep
from app.core.errors import ConflictError
from app.models import Invoice
from app.models.enums import ActionKind
from app.paypal.deps import PayPalDep
from app.schemas.action import ActionRead
from app.schemas.invoice import InvoiceRead
from app.schemas.response import ApiResponse, success
from app.services import actions as action_service
from app.services import invoicing as invoice_service
from app.services import milestones as milestone_service

router = APIRouter(tags=["invoices"])


@router.get("/invoices", response_model=ApiResponse[list[InvoiceRead]])
async def list_invoices(
    user: CurrentUser, session: SessionDep
) -> ApiResponse[list[InvoiceRead]]:
    invoices = await invoice_service.list_invoices(session, user.id)
    return success([InvoiceRead.model_validate(item) for item in invoices])


@router.get("/invoices/{invoice_id}", response_model=ApiResponse[InvoiceRead])
async def get_invoice(
    invoice_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[InvoiceRead]:
    invoice = await invoice_service.get_invoice(session, invoice_id, user.id)
    return success(InvoiceRead.model_validate(invoice))


@router.post(
    "/milestones/{milestone_id}/invoice",
    response_model=ApiResponse[ActionRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def propose_invoice(
    milestone_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[ActionRead]:
    milestone = await milestone_service.get_milestone(session, milestone_id, user.id)
    existing = await session.scalar(
        select(Invoice).where(Invoice.milestone_id == milestone.id)
    )
    if existing is not None:
        raise ConflictError("This milestone already has an invoice.")
    action = await action_service.propose(
        session,
        owner_id=user.id,
        kind=ActionKind.CREATE_INVOICE,
        payload={"milestone_id": str(milestone.id)},
        rationale=f"Bill '{milestone.title}' for {milestone.amount}.",
        dedupe_key=f"invoice:{milestone.id}",
    )
    await session.commit()
    return success(ActionRead.model_validate(action))


@router.post(
    "/invoices/{invoice_id}/remind",
    response_model=ApiResponse[ActionRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def propose_reminder(
    invoice_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[ActionRead]:
    invoice = await invoice_service.get_invoice(session, invoice_id, user.id)
    if invoice.status.value in {"paid", "cancelled"}:
        raise ConflictError(f"Invoice is already {invoice.status.value}.")
    action = await action_service.propose(
        session,
        owner_id=user.id,
        kind=ActionKind.SEND_REMINDER,
        payload={"invoice_id": str(invoice.id)},
        rationale=f"Send a reminder for invoice {invoice.number or invoice.id}.",
        dedupe_key=f"reminder:{invoice.id}:{date.today().isoformat()}",
    )
    await session.commit()
    return success(ActionRead.model_validate(action))


@router.post(
    "/invoices/{invoice_id}/cancel",
    response_model=ApiResponse[ActionRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def propose_cancel(
    invoice_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[ActionRead]:
    invoice = await invoice_service.get_invoice(session, invoice_id, user.id)
    action = await action_service.propose(
        session,
        owner_id=user.id,
        kind=ActionKind.CANCEL_INVOICE,
        payload={"invoice_id": str(invoice.id)},
        rationale=f"Cancel invoice {invoice.number or invoice.id}.",
        dedupe_key=f"cancel:{invoice.id}",
    )
    await session.commit()
    return success(ActionRead.model_validate(action))


@router.post(
    "/invoices/{invoice_id}/payout",
    response_model=ApiResponse[ActionRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def propose_payout(
    invoice_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[ActionRead]:
    invoice = await invoice_service.get_invoice(session, invoice_id, user.id)
    if invoice.status.value != "paid":
        raise ConflictError("The invoice is not paid yet.")
    action = await action_service.propose(
        session,
        owner_id=user.id,
        kind=ActionKind.PREPARE_PAYOUT,
        payload={"invoice_id": str(invoice.id)},
        rationale="Prepare the team split for this paid invoice.",
        dedupe_key=f"payout:{invoice.id}",
    )
    await session.commit()
    return success(ActionRead.model_validate(action))


@router.post("/invoices/{invoice_id}/refresh", response_model=ApiResponse[InvoiceRead])
async def refresh_invoice(
    invoice_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    paypal: PayPalDep,
) -> ApiResponse[InvoiceRead]:
    invoice = await invoice_service.sync_from_paypal(
        session, paypal, invoice_id=invoice_id, owner_id=user.id
    )
    await session.commit()
    await session.refresh(invoice)
    return success(InvoiceRead.model_validate(invoice))
