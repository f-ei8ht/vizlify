from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.config import settings


async def _executed_payout(api: AsyncClient) -> dict[str, Any]:
    project = (await api.get("/projects")).json()["data"][0]
    milestone = (await api.get(f"/projects/{project['id']}/milestones")).json()["data"][0]
    invoice_proposal = (
        await api.post(f"/milestones/{milestone['id']}/invoice")
    ).json()["data"]
    await api.post(f"/actions/{invoice_proposal['id']}/approve")
    invoice = (await api.get("/invoices")).json()["data"][0]

    await api.post(
        "/webhooks/paypal",
        json={
            "id": f"WH-{uuid4()}",
            "event_type": "INVOICING.INVOICE.PAID",
            "resource": {"id": invoice["paypal_invoice_id"], "status": "PAID"},
        },
    )
    payout_proposal = (await api.post(f"/invoices/{invoice['id']}/payout")).json()["data"]
    await api.post(f"/actions/{payout_proposal['id']}/approve")
    payout = (await api.get("/payouts")).json()["data"][0]

    execute = (await api.post(f"/payouts/{payout['id']}/execute")).json()["data"]
    await api.post(f"/actions/{execute['id']}/approve")
    return (await api.get(f"/payouts/{payout['id']}")).json()["data"]


async def test_bad_signature_is_rejected(
    seeded_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "PAYPAL_MODE", "sandbox")
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "wh-test")

    response = await seeded_client.post(
        "/webhooks/paypal",
        json={
            "id": "WH-BAD",
            "event_type": "INVOICING.INVOICE.PAID",
            "resource": {"id": "INV2-NOPE"},
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


async def test_cancelled_webhook_updates_the_invoice(seeded_client: AsyncClient) -> None:
    project = (await seeded_client.get("/projects")).json()["data"][0]
    milestone = (await seeded_client.get(f"/projects/{project['id']}/milestones")).json()[
        "data"
    ][0]
    proposal = (await seeded_client.post(f"/milestones/{milestone['id']}/invoice")).json()[
        "data"
    ]
    await seeded_client.post(f"/actions/{proposal['id']}/approve")
    invoice = (await seeded_client.get("/invoices")).json()["data"][0]

    response = await seeded_client.post(
        "/webhooks/paypal",
        json={
            "id": f"WH-{uuid4()}",
            "event_type": "INVOICING.INVOICE.CANCELLED",
            "resource": {"id": invoice["paypal_invoice_id"], "status": "CANCELLED"},
        },
    )

    assert response.status_code == 200
    stored = (await seeded_client.get(f"/invoices/{invoice['id']}")).json()["data"]
    assert stored["status"] == "cancelled"


async def test_batch_webhook_updates_the_payout(seeded_client: AsyncClient) -> None:
    payout = await _executed_payout(seeded_client)
    batch_id = payout["paypal_batch_id"]

    response = await seeded_client.post(
        "/webhooks/paypal",
        json={
            "id": f"WH-{uuid4()}",
            "event_type": "PAYMENT.PAYOUTSBATCH.SUCCESS",
            "resource": {"batch_header": {"payout_batch_id": batch_id}},
        },
    )

    assert response.status_code == 200
    stored = (await seeded_client.get(f"/payouts/{payout['id']}")).json()["data"]
    assert stored["status"] == "success"


async def test_item_webhook_updates_one_item(seeded_client: AsyncClient) -> None:
    payout = await _executed_payout(seeded_client)
    item = payout["items"][0]

    response = await seeded_client.post(
        "/webhooks/paypal",
        json={
            "id": f"WH-{uuid4()}",
            "event_type": "PAYMENT.PAYOUTS-ITEM.SUCCEEDED",
            "resource": {
                "payout_item_id": "PAYOUT-ITEM-1",
                "payout_batch_id": payout["paypal_batch_id"],
                "payout_item": {"sender_item_id": item["id"]},
            },
        },
    )

    assert response.status_code == 200
    stored = (await seeded_client.get(f"/payouts/{payout['id']}")).json()["data"]
    updated = next(row for row in stored["items"] if row["id"] == item["id"])
    assert updated["status"] == "success"
    assert updated["paypal_item_id"] == "PAYOUT-ITEM-1"


async def test_malformed_webhook_is_rejected(seeded_client: AsyncClient) -> None:
    response = await seeded_client.post("/webhooks/paypal", json={"event_type": "X"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
