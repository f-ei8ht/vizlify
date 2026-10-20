from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.errors import ConflictError
from app.models import TeamMember
from app.services.payouts import allocate_split


def _member(name: str, share: str) -> TeamMember:
    return TeamMember(
        project_id=uuid4(),
        name=name,
        paypal_email=f"{name.lower()}@example.com",
        share_percent=Decimal(share),
    )


def test_split_uses_largest_remainder_and_sums_exactly() -> None:
    members = [_member("Rida", "33.33"), _member("Maya", "33.33"), _member("Sam", "33.34")]

    allocations = allocate_split(Decimal("100.00"), members)

    assert [amount for _, amount in allocations] == [
        Decimal("33.33"),
        Decimal("33.33"),
        Decimal("33.34"),
    ]
    assert sum(amount for _, amount in allocations) == Decimal("100.00")


def test_split_is_deterministic_on_a_tie() -> None:
    members = [_member("Zoe", "33.33"), _member("Ada", "33.33"), _member("Mia", "33.34")]

    first = allocate_split(Decimal("10.00"), members)
    second = allocate_split(Decimal("10.00"), members)

    assert first == second
    assert sum(amount for _, amount in first) == Decimal("10.00")


def test_split_keeps_the_agency_share_when_team_is_under_100() -> None:
    members = [_member("Rida", "40.00"), _member("Maya", "35.00")]

    allocations = allocate_split(Decimal("100.00"), members)

    assert sum(amount for _, amount in allocations) == Decimal("75.00")


def test_split_needs_members() -> None:
    with pytest.raises(ConflictError):
        allocate_split(Decimal("100.00"), [])


async def _paid_invoice(api: AsyncClient) -> dict[str, Any]:
    project = (await api.get("/projects")).json()["data"][0]
    milestone = (await api.get(f"/projects/{project['id']}/milestones")).json()["data"][0]
    proposal = (await api.post(f"/milestones/{milestone['id']}/invoice")).json()["data"]
    await api.post(f"/actions/{proposal['id']}/approve")
    invoice = (await api.get("/invoices")).json()["data"][0]

    event = {
        "id": f"WH-{uuid4()}",
        "event_type": "INVOICING.INVOICE.PAID",
        "resource": {"id": invoice["paypal_invoice_id"], "status": "PAID"},
    }
    paid = await api.post("/webhooks/paypal", json=event)
    assert paid.status_code == 200
    return (await api.get(f"/invoices/{invoice['id']}")).json()["data"]


async def _prepare_payout(api: AsyncClient, invoice: dict[str, Any]) -> dict[str, Any]:
    proposal = (await api.post(f"/invoices/{invoice['id']}/payout")).json()["data"]
    approved = await api.post(f"/actions/{proposal['id']}/approve")
    assert approved.status_code == 200
    return (await api.get("/payouts")).json()["data"][0]


async def test_paid_invoice_creates_a_payout_proposal(seeded_client: AsyncClient) -> None:
    invoice = await _paid_invoice(seeded_client)

    queue = (await seeded_client.get("/actions?status=pending")).json()["data"]
    kinds = [item["kind"] for item in queue]

    assert invoice["status"] == "paid"
    assert "prepare_payout" in kinds


async def test_payout_items_match_the_team_split(seeded_client: AsyncClient) -> None:
    invoice = await _paid_invoice(seeded_client)
    payout = await _prepare_payout(seeded_client, invoice)

    amounts = sorted((item["amount"] for item in payout["items"]), key=Decimal)

    assert payout["total"] == "2500.00"
    assert amounts == ["625.00", "875.00", "1000.00"]


async def test_executing_a_payout_creates_a_batch(seeded_client: AsyncClient) -> None:
    invoice = await _paid_invoice(seeded_client)
    payout = await _prepare_payout(seeded_client, invoice)

    action = (
        await seeded_client.post(f"/payouts/{payout['id']}/execute")
    ).json()["data"]
    approved = await seeded_client.post(f"/actions/{action['id']}/approve")

    assert approved.status_code == 200
    stored = (await seeded_client.get(f"/payouts/{payout['id']}")).json()["data"]
    assert stored["paypal_batch_id"].startswith("MOCK-BATCH-")
    assert stored["status"] == "pending"


async def test_payout_over_the_spend_cap_is_blocked(
    seeded_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    invoice = await _paid_invoice(seeded_client)
    monkeypatch.setattr(settings, "PAYOUT_MAX_PER_ACTION", Decimal("100.00"))
    proposal = (await seeded_client.post(f"/invoices/{invoice['id']}/payout")).json()["data"]

    response = await seeded_client.post(f"/actions/{proposal['id']}/approve")

    assert response.status_code == 409
    stored = (await seeded_client.get(f"/actions/{proposal['id']}")).json()["data"]
    assert stored["status"] == "failed"
    assert "cap" in stored["error"]


async def test_payout_over_the_daily_cap_is_blocked(
    seeded_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    invoice = await _paid_invoice(seeded_client)
    monkeypatch.setattr(settings, "PAYOUT_MAX_PER_ACTION", Decimal("10000.00"))
    monkeypatch.setattr(settings, "PAYOUT_MAX_PER_DAY", Decimal("100.00"))
    proposal = (await seeded_client.post(f"/invoices/{invoice['id']}/payout")).json()["data"]

    response = await seeded_client.post(f"/actions/{proposal['id']}/approve")

    assert response.status_code == 409
    assert "daily cap" in response.json()["error"]["message"]


async def test_duplicate_paid_webhook_does_not_duplicate_the_proposal(
    seeded_client: AsyncClient,
) -> None:
    project = (await seeded_client.get("/projects")).json()["data"][0]
    milestone = (await seeded_client.get(f"/projects/{project['id']}/milestones")).json()[
        "data"
    ][0]
    proposal = (await seeded_client.post(f"/milestones/{milestone['id']}/invoice")).json()[
        "data"
    ]
    await seeded_client.post(f"/actions/{proposal['id']}/approve")
    invoice = (await seeded_client.get("/invoices")).json()["data"][0]

    event = {
        "id": "WH-DUPLICATE",
        "event_type": "INVOICING.INVOICE.PAID",
        "resource": {"id": invoice["paypal_invoice_id"], "status": "PAID"},
    }
    first = await seeded_client.post("/webhooks/paypal", json=event)
    second = await seeded_client.post("/webhooks/paypal", json=event)

    pending = (await seeded_client.get("/actions?status=pending")).json()["data"]
    payout_proposals = [item for item in pending if item["kind"] == "prepare_payout"]
    assert first.json()["data"]["status"] == "processed"
    assert second.json()["data"]["status"] == "duplicate"
    assert len(payout_proposals) == 1


async def test_unknown_payout_is_not_found(seeded_client: AsyncClient) -> None:
    response = await seeded_client.get(f"/payouts/{uuid4()}")

    assert response.status_code == 404
