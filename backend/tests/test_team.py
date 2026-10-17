from httpx import AsyncClient


async def _project_id(api: AsyncClient) -> str:
    response = await api.get("/projects")
    return response.json()["data"][0]["id"]


async def test_list_team(seeded_client: AsyncClient) -> None:
    project_id = await _project_id(seeded_client)

    response = await seeded_client.get(f"/projects/{project_id}/team")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 3


async def test_shares_cannot_exceed_one_hundred_percent(seeded_client: AsyncClient) -> None:
    project_id = await _project_id(seeded_client)

    response = await seeded_client.post(
        f"/projects/{project_id}/team",
        json={"name": "Extra", "paypal_email": "extra@northwind.dev", "share_percent": "10.00"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_add_and_update_a_team_member(seeded_client: AsyncClient) -> None:
    client = (
        await seeded_client.post(
            "/clients", json={"name": "Initech", "email": "billing@initech.dev"}
        )
    ).json()["data"]
    project = (
        await seeded_client.post(
            "/projects", json={"client_id": client["id"], "name": "Rebrand", "currency": "USD"}
        )
    ).json()["data"]

    created = await seeded_client.post(
        f"/projects/{project['id']}/team",
        json={"name": "Ann", "paypal_email": "ann@initech.dev", "share_percent": "60.00"},
    )
    updated = await seeded_client.patch(
        f"/team/{created.json()['data']['id']}", json={"share_percent": "50.00"}
    )

    assert created.status_code == 201
    assert updated.json()["data"]["share_percent"] == "50.00"
