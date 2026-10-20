from typing import Any
from uuid import uuid4

from httpx import AsyncClient


async def _sent_invoice(api: AsyncClient) -> dict[str, Any]:
    project = (await api.get("/projects")).json()["data"][0]
    milestone = (await api.get(f"/projects/{project['id']}/milestones")).json()["data"][0]
    proposal = (await api.post(f"/milestones/{milestone['id']}/invoice")).json()["data"]
    await api.post(f"/actions/{proposal['id']}/approve")
    return (await api.get("/invoices")).json()["data"][0]


async def test_invoice_detail_and_list(seeded_client: AsyncClient) -> None:
    invoice = await _sent_invoice(seeded_client)

    detail = await seeded_client.get(f"/invoices/{invoice['id']}")

    assert detail.status_code == 200
    assert detail.json()["data"]["paypal_invoice_id"].startswith("MOCK-INV-")
    assert detail.json()["data"]["number"] == "VIZ-0001"


async def test_reminder_is_a_proposal(seeded_client: AsyncClient) -> None:
    invoice = await _sent_invoice(seeded_client)

    proposed = await seeded_client.post(f"/invoices/{invoice['id']}/remind")
    action = proposed.json()["data"]
    approved = await seeded_client.post(f"/actions/{action['id']}/approve")

    assert proposed.status_code == 202
    assert action["kind"] == "send_reminder"
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "executed"


async def test_cancel_updates_the_local_status(seeded_client: AsyncClient) -> None:
    invoice = await _sent_invoice(seeded_client)

    action = (await seeded_client.post(f"/invoices/{invoice['id']}/cancel")).json()["data"]
    await seeded_client.post(f"/actions/{action['id']}/approve")

    detail = (await seeded_client.get(f"/invoices/{invoice['id']}")).json()["data"]
    assert detail["status"] == "cancelled"


async def test_refresh_pulls_the_paypal_status(seeded_client: AsyncClient) -> None:
    invoice = await _sent_invoice(seeded_client)

    refreshed = await seeded_client.post(f"/invoices/{invoice['id']}/refresh")

    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["status"] == "sent"


async def test_a_milestone_cannot_be_invoiced_twice(seeded_client: AsyncClient) -> None:
    invoice = await _sent_invoice(seeded_client)
    project = (await seeded_client.get("/projects")).json()["data"][0]
    milestone = (await seeded_client.get(f"/projects/{project['id']}/milestones")).json()[
        "data"
    ][0]

    response = await seeded_client.post(f"/milestones/{milestone['id']}/invoice")

    assert response.status_code == 409
    assert invoice["status"] == "sent"


async def test_unknown_invoice_is_not_found(seeded_client: AsyncClient) -> None:
    response = await seeded_client.get(f"/invoices/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
