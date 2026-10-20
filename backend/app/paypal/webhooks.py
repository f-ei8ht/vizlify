"""Webhook signature verification through PayPal's Notifications API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.paypal.client import PayPalClient

_HEADER_FIELDS = {
    "auth_algo": "paypal-auth-algo",
    "cert_url": "paypal-cert-url",
    "transmission_id": "paypal-transmission-id",
    "transmission_sig": "paypal-transmission-sig",
    "transmission_time": "paypal-transmission-time",
}


async def verify_webhook(
    client: PayPalClient,
    *,
    headers: Mapping[str, str],
    event: dict[str, Any],
    webhook_id: str,
) -> bool:
    lower = {name.lower(): value for name, value in headers.items()}
    payload: dict[str, Any] = {"webhook_id": webhook_id, "webhook_event": event}
    for field, header in _HEADER_FIELDS.items():
        value = lower.get(header)
        if not value:
            return False
        payload[field] = value

    response = await client.post("/v1/notifications/verify-webhook-signature", json=payload)
    return (response.payload or {}).get("verification_status") == "SUCCESS"
