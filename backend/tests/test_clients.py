from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, User

_NEW_CLIENT = {"name": "Initech", "email": "billing@initech.dev"}


async def _create(api: AsyncClient) -> dict:
    response = await api.post("/clients", json=_NEW_CLIENT)
    return response.json()["data"]


async def test_list_returns_seeded_clients(seeded_client: AsyncClient) -> None:
    response = await seeded_client.get("/clients")

    assert response.status_code == 200
    assert "Acme Co" in [item["name"] for item in response.json()["data"]]


async def test_create_client(seeded_client: AsyncClient) -> None:
    response = await seeded_client.post("/clients", json=_NEW_CLIENT)

    assert response.status_code == 201
    body = response.json()
    assert body["error"] is None
    assert body["data"]["name"] == "Initech"
    assert body["data"]["tone_preference"] == "friendly"


async def test_update_client(seeded_client: AsyncClient) -> None:
    client = await _create(seeded_client)

    response = await seeded_client.patch(
        f"/clients/{client['id']}", json={"tone_preference": "firm"}
    )

    assert response.json()["data"]["tone_preference"] == "firm"


async def test_delete_client(seeded_client: AsyncClient) -> None:
    client = await _create(seeded_client)

    deleted = await seeded_client.delete(f"/clients/{client['id']}")
    missing = await seeded_client.get(f"/clients/{client['id']}")

    assert deleted.status_code == 200
    assert deleted.json()["data"] is None
    assert missing.status_code == 404


async def test_deleting_a_client_deletes_its_projects(seeded_client: AsyncClient) -> None:
    project = (await seeded_client.get("/projects")).json()["data"][0]

    deleted = await seeded_client.delete(f"/clients/{project['client_id']}")
    missing = await seeded_client.get(f"/projects/{project['id']}")

    assert deleted.status_code == 200
    assert missing.status_code == 404


async def test_missing_client_uses_error_envelope(seeded_client: AsyncClient) -> None:
    response = await seeded_client.get(f"/clients/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_invalid_payload_is_a_validation_error(seeded_client: AsyncClient) -> None:
    response = await seeded_client.post("/clients", json={"name": "", "email": "nope"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]


async def test_clients_are_scoped_to_the_owner(
    seeded_client: AsyncClient, db_session: AsyncSession
) -> None:
    other = User(email="other@studio.dev")
    db_session.add(other)
    await db_session.commit()
    db_session.add(Client(owner_id=other.id, name="Hidden Co", email="hidden@studio.dev"))
    await db_session.commit()

    response = await seeded_client.get("/clients")

    assert "Hidden Co" not in [item["name"] for item in response.json()["data"]]
