"""An in-process PayPal stand-in, so the app runs and demos without keys.

It plugs in at the transport layer: the real client, headers, token cache and
parsing all run unchanged. Only the last hop is faked, so switching to the
sandbox is one environment variable.
"""

from __future__ import annotations

import itertools
import json
from typing import Any

import httpx


def build_mock_transport() -> httpx.MockTransport:
    invoice_ids = itertools.count(1)
    payout_ids = itertools.count(1)
    invoice_numbers = itertools.count(1)
    idempotent_results: dict[str, tuple[int, dict[str, str], dict[str, Any] | None]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = _json_body(request)
        request_id = request.headers.get("PayPal-Request-Id")

        if path == "/v1/oauth2/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "mock-access-token",
                    "token_type": "Bearer",
                    "expires_in": 32400,
                },
            )

        if path == "/v2/invoicing/generate-next-invoice-number":
            return httpx.Response(200, json={"invoice_number": f"VIZ-{next(invoice_numbers):04d}"})

        if request_id and request_id in idempotent_results:
            status, headers, payload = idempotent_results[request_id]
            return httpx.Response(status, headers=headers, json=payload)

        if path == "/v2/invoicing/invoices" and request.method == "POST":
            invoice_id = f"MOCK-INV-{next(invoice_ids):04d}"
            payload = {
                "id": invoice_id,
                "status": "DRAFT",
                "detail": {
                    "invoice_number": body.get("detail", {}).get("invoice_number", "VIZ-0000"),
                    "currency_code": body.get("detail", {}).get("currency_code", "USD"),
                },
            }
            location = (
                f"{request.url.scheme}://{request.url.netloc}/v2/invoicing/invoices/{invoice_id}"
            )
            response = httpx.Response(
                201,
                headers={"Location": location},
                json=payload,
            )
            _remember(idempotent_results, request_id, response)
            return response

        if path.startswith("/v2/invoicing/invoices/") and request.method == "POST":
            return httpx.Response(200)

        if path.startswith("/v2/invoicing/invoices/") and request.method == "GET":
            invoice_id = path.rstrip("/").rsplit("/", 1)[-1]
            return httpx.Response(200, json={"id": invoice_id, "status": "SENT"})

        if path == "/v1/payments/payouts" and request.method == "POST":
            batch_id = f"MOCK-BATCH-{next(payout_ids):04d}"
            payload = {
                "batch_header": {
                    "payout_batch_id": batch_id,
                    "batch_status": "PENDING",
                    "sender_batch_header": body.get("sender_batch_header", {}),
                }
            }
            response = httpx.Response(201, json=payload)
            _remember(idempotent_results, request_id, response)
            return response

        if path == "/v1/notifications/verify-webhook-signature":
            return httpx.Response(200, json={"verification_status": "SUCCESS"})

        return httpx.Response(
            404,
            json={
                "name": "MOCK_ROUTE_NOT_IMPLEMENTED",
                "message": f"The mock PayPal transport does not handle {request.method} {path}.",
                "debug_id": "mock",
            },
        )

    return httpx.MockTransport(handler)


def _json_body(request: httpx.Request) -> dict[str, Any]:
    if not request.content:
        return {}
    try:
        parsed = json.loads(request.content)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _remember(
    cache: dict[str, tuple[int, dict[str, str], dict[str, Any] | None]],
    request_id: str | None,
    response: httpx.Response,
) -> None:
    if request_id:
        cache[request_id] = (response.status_code, dict(response.headers), response.json())
