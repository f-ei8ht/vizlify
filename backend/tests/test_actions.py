from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, PendingAction, User
from app.models.enums import ActionKind, ActionStatus


async def _first_milestone(api: AsyncClient) -> dict[str, Any]:
    project = (await api.get("/projects")).json()["data"][0]
    milestones = (await api.get(f"/projects/{project['id']}/milestones")).json()["data"]
    return milestones[0]


async def _propose_invoice(api: AsyncClient) -> dict[str, Any]:
    milestone = await _first_milestone(api)
    response = await api.post(f"/milestones/{milestone['id']}/invoice")
    assert response.status_code == 202
    return response.json()["data"]


async def _approve(api: AsyncClient, action_id: str):
    return await api.post(f"/actions/{action_id}/approve")


async def test_marking_a_milestone_done_creates_a_proposal(
    seeded_client: AsyncClient,
) -> None:
    milestone = await _first_milestone(seeded_client)

    updated = await seeded_client.patch(
        f"/milestones/{milestone['id']}", json={"status": "done"}
    )
    queue = await seeded_client.get("/actions?status=pending")

    assert updated.status_code == 200
    proposals = queue.json()["data"]
    assert len(proposals) == 1
    assert proposals[0]["kind"] == "create_invoice"
    assert proposals[0]["payload"] == {"milestone_id": milestone["id"]}
    assert "done" in proposals[0]["rationale"]


async def test_approving_an_invoice_proposal_creates_and_sends_it(
    seeded_client: AsyncClient,
) -> None:
    action = await _propose_invoice(seeded_client)

    approved = await _approve(seeded_client, action["id"])

    assert approved.status_code == 200
    body = approved.json()["data"]
    assert body["status"] == "executed"
    assert body["result"]["number"] == "VIZ-0001"
    assert body["result"]["status"] == "sent"

    invoices = (await seeded_client.get("/invoices")).json()["data"]
    assert len(invoices) == 1
    assert invoices[0]["status"] == "sent"
    assert invoices[0]["amount"] == "2500.00"

    milestone = await _first_milestone(seeded_client)
    assert milestone["status"] == "billed"


async def test_double_approve_is_a_conflict(seeded_client: AsyncClient) -> None:
    action = await _propose_invoice(seeded_client)
    assert (await _approve(seeded_client, action["id"])).status_code == 200

    second = await _approve(seeded_client, action["id"])

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"
    invoices = (await seeded_client.get("/invoices")).json()["data"]
    assert len(invoices) == 1


async def test_rejecting_needs_a_reason_and_closes_the_proposal(
    seeded_client: AsyncClient,
) -> None:
    action = await _propose_invoice(seeded_client)

    missing = await seeded_client.post(f"/actions/{action['id']}/reject", json={})
    rejected = await seeded_client.post(
        f"/actions/{action['id']}/reject", json={"reason": "Waiting for sign-off"}
    )

    assert missing.status_code == 422
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "rejected"
    assert rejected.json()["data"]["result"] == {"reason": "Waiting for sign-off"}
    assert (await _approve(seeded_client, action["id"])).status_code == 409


async def test_approval_writes_an_audit_trail(
    seeded_client: AsyncClient, db_session: AsyncSession
) -> None:
    action = await _propose_invoice(seeded_client)
    await _approve(seeded_client, action["id"])

    rows = list(await db_session.scalars(select(AuditLog)))
    actions = {row.action for row in rows}

    assert {"proposed", "approved", "executed"} <= actions
    executed = next(row for row in rows if row.action == "executed")
    assert executed.entity == "pending_action"
    assert executed.entity_id == action["id"]


async def test_a_failed_execution_marks_the_proposal_failed(
    seeded_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await db_session.scalar(select(User).where(User.email == "demo@vizlify.space"))
    assert user is not None
    user.paypal_email = None
    await db_session.commit()

    action = await _propose_invoice(seeded_client)
    response = await _approve(seeded_client, action["id"])

    assert response.status_code == 409
    stored = (await seeded_client.get(f"/actions/{action['id']}")).json()["data"]
    assert stored["status"] == "failed"
    assert stored["error"] == "Set your PayPal email before creating an invoice."


async def test_proposals_are_owner_scoped(
    seeded_client: AsyncClient, db_session: AsyncSession
) -> None:
    other = User(email="other@studio.dev")
    db_session.add(other)
    await db_session.flush()
    hidden = PendingAction(
        owner_id=other.id,
        kind=ActionKind.CREATE_INVOICE,
        dedupe_key="hidden-proposal",
        payload={"milestone_id": "00000000-0000-0000-0000-000000000000"},
        rationale="Should never be visible",
        status=ActionStatus.PENDING,
    )
    db_session.add(hidden)
    await db_session.commit()

    listed = (await seeded_client.get("/actions")).json()["data"]
    fetched = await seeded_client.get(f"/actions/{hidden.id}")
    approved = await _approve(seeded_client, str(hidden.id))

    assert hidden.id not in [item["id"] for item in listed]
    assert fetched.status_code == 404
    assert approved.status_code == 404


async def test_action_status_filter(seeded_client: AsyncClient) -> None:
    action = await _propose_invoice(seeded_client)
    await _approve(seeded_client, action["id"])

    pending = (await seeded_client.get("/actions?status=pending")).json()["data"]
    executed = (await seeded_client.get("/actions?status=executed")).json()["data"]

    assert pending == []
    assert [item["id"] for item in executed] == [action["id"]]
