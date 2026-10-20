"""Invoicing v2 calls, built on the shared PayPal transport."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.paypal.client import PayPalClient


async def generate_invoice_number(client: PayPalClient) -> str:
    response = await client.post("/v2/invoicing/generate-next-invoice-number")
    number = (response.payload or {}).get("invoice_number")
    if not isinstance(number, str) or not number:
        raise ValueError("PayPal returned no invoice number.")
    return number


async def create_draft_invoice(
    client: PayPalClient,
    *,
    invoice_number: str,
    currency: str,
    invoicer_email: str,
    recipient_email: str,
    item_name: str,
    amount: Decimal,
    note: str,
    request_id: str,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "detail": {
            "invoice_number": invoice_number,
            "currency_code": currency,
            "note": note,
        },
        "invoicer": {"email_address": invoicer_email},
        "primary_recipients": [{"billing_info": {"email_address": recipient_email}}],
        "items": [
            {
                "name": item_name,
                "quantity": "1",
                "unit_amount": {"currency_code": currency, "value": f"{amount:.2f}"},
            }
        ],
    }
    response = await client.post(
        "/v2/invoicing/invoices", json=payload, request_id=request_id
    )
    body = response.payload or {}
    invoice_id = body.get("id")
    if not isinstance(invoice_id, str) or not invoice_id:
        invoice_id = _invoice_id_from_location(response.header("Location"))
    if not invoice_id:
        raise ValueError("PayPal returned no invoice id.")
    return invoice_id, body


async def send_invoice(client: PayPalClient, invoice_id: str, *, request_id: str) -> None:
    await client.post(
        f"/v2/invoicing/invoices/{invoice_id}/send",
        json={"send_to_recipient": True, "send_to_invoicer": True},
        request_id=request_id,
    )


async def remind_invoice(
    client: PayPalClient,
    invoice_id: str,
    *,
    subject: str,
    note: str,
    request_id: str,
) -> None:
    await client.post(
        f"/v2/invoicing/invoices/{invoice_id}/remind",
        json={"subject": subject, "note": note, "send_to_recipient": True},
        request_id=request_id,
    )


async def cancel_invoice(
    client: PayPalClient,
    invoice_id: str,
    *,
    subject: str,
    note: str,
    request_id: str,
) -> None:
    await client.post(
        f"/v2/invoicing/invoices/{invoice_id}/cancel",
        json={
            "subject": subject,
            "note": note,
            "send_to_recipient": True,
            "send_to_invoicer": True,
        },
        request_id=request_id,
    )


async def get_invoice(client: PayPalClient, invoice_id: str) -> dict[str, Any]:
    response = await client.get(f"/v2/invoicing/invoices/{invoice_id}")
    return response.payload or {}


def _invoice_id_from_location(location: str | None) -> str | None:
    if not location:
        return None
    return location.rstrip("/").rsplit("/", 1)[-1] or None
