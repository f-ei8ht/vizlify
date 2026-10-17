from uuid import uuid4

from httpx import AsyncClient


async def _create_client_id(api: AsyncClient) -> str:
    response = await api.post(
        "/clients", json={"name": "Initech", "email": "billing@initech.dev"}
    )
    return response.json()["data"]["id"]


async def test_list_returns_the_seeded_project(seeded_client: AsyncClient) -> None:
    response = await seeded_client.get("/projects")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_create_project(seeded_client: AsyncClient) -> None:
    client_id = await _create_client_id(seeded_client)

    response = await seeded_client.post(
        "/projects", json={"client_id": client_id, "name": "Rebrand", "currency": "USD"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["name"] == "Rebrand"
    assert body["data"]["status"] == "active"


async def test_project_for_unknown_client_is_not_found(seeded_client: AsyncClient) -> None:
    response = await seeded_client.post(
        "/projects", json={"client_id": str(uuid4()), "name": "Ghost", "currency": "USD"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_delete_project(seeded_client: AsyncClient) -> None:
    project_id = (await seeded_client.get("/projects")).json()["data"][0]["id"]

    deleted = await seeded_client.delete(f"/projects/{project_id}")
    missing = await seeded_client.get(f"/projects/{project_id}")

    assert deleted.status_code == 200
    assert missing.status_code == 404
