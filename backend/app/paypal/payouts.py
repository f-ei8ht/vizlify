"""Payouts v1 batch calls, built on the shared PayPal transport."""

from __future__ import annotations

from typing import Any

from app.paypal.client import PayPalClient


async def create_payout_batch(
    client: PayPalClient,
    *,
    sender_batch_id: str,
    currency: str,
    items: list[dict[str, Any]],
    request_id: str,
) -> dict[str, Any]:
    payload = {
        "sender_batch_header": {
            "sender_batch_id": sender_batch_id,
            "email_subject": "You have a payout from Vizlify",
            "email_message": "Your share of a client payment has been sent.",
        },
        "items": items,
    }
    response = await client.post(
        "/v1/payments/payouts", json=payload, request_id=request_id
    )
    return response.payload or {}


def batch_id_from_response(payload: dict[str, Any]) -> str | None:
    header = payload.get("batch_header")
    if not isinstance(header, dict):
        return None
    batch_id = header.get("payout_batch_id")
    return batch_id if isinstance(batch_id, str) and batch_id else None
