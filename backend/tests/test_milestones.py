from uuid import uuid4

from httpx import AsyncClient


async def _project_id(api: AsyncClient) -> str:
    response = await api.get("/projects")
    return response.json()["data"][0]["id"]


async def test_list_returns_seeded_milestones(seeded_client: AsyncClient) -> None:
    project_id = await _project_id(seeded_client)

    response = await seeded_client.get(f"/projects/{project_id}/milestones")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 3


async def test_create_milestone(seeded_client: AsyncClient) -> None:
    project_id = await _project_id(seeded_client)

    response = await seeded_client.post(
        f"/projects/{project_id}/milestones",
        json={"title": "Extras", "amount": "500.00"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["title"] == "Extras"
    assert response.json()["data"]["status"] == "todo"


async def test_update_milestone_status(seeded_client: AsyncClient) -> None:
    project_id = await _project_id(seeded_client)
    milestone = (
        await seeded_client.post(
            f"/projects/{project_id}/milestones",
            json={"title": "Extras", "amount": "500.00"},
        )
    ).json()["data"]

    response = await seeded_client.patch(
        f"/milestones/{milestone['id']}", json={"status": "done"}
    )

    assert response.json()["data"]["status"] == "done"


async def test_unknown_milestone_is_not_found(seeded_client: AsyncClient) -> None:
    response = await seeded_client.patch(
        f"/milestones/{uuid4()}", json={"status": "done"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_delete_milestone(seeded_client: AsyncClient) -> None:
    project_id = await _project_id(seeded_client)
    milestone = (
        await seeded_client.post(
            f"/projects/{project_id}/milestones",
            json={"title": "Extras", "amount": "500.00"},
        )
    ).json()["data"]

    deleted = await seeded_client.delete(f"/milestones/{milestone['id']}")

    assert deleted.status_code == 200
    assert deleted.json()["data"] is None
