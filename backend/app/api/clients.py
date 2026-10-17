from uuid import UUID

from fastapi import APIRouter, status

from app.auth.deps import CurrentUser, SessionDep
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.schemas.response import ApiResponse, success
from app.services import clients as client_service

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=ApiResponse[list[ClientRead]])
async def list_clients(user: CurrentUser, session: SessionDep) -> ApiResponse[list[ClientRead]]:
    clients = await client_service.list_clients(session, user.id)
    return success([ClientRead.model_validate(client) for client in clients])


@router.post("", response_model=ApiResponse[ClientRead], status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate, user: CurrentUser, session: SessionDep
) -> ApiResponse[ClientRead]:
    client = await client_service.create_client(session, user.id, payload)
    return success(ClientRead.model_validate(client))


@router.get("/{client_id}", response_model=ApiResponse[ClientRead])
async def get_client(
    client_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[ClientRead]:
    client = await client_service.get_client(session, client_id, user.id)
    return success(ClientRead.model_validate(client))


@router.patch("/{client_id}", response_model=ApiResponse[ClientRead])
async def update_client(
    client_id: UUID, payload: ClientUpdate, user: CurrentUser, session: SessionDep
) -> ApiResponse[ClientRead]:
    client = await client_service.get_client(session, client_id, user.id)
    updated = await client_service.update_client(session, client, payload)
    return success(ClientRead.model_validate(updated))


@router.delete("/{client_id}", response_model=ApiResponse[None])
async def delete_client(
    client_id: UUID, user: CurrentUser, session: SessionDep
) -> ApiResponse[None]:
    client = await client_service.get_client(session, client_id, user.id)
    await client_service.delete_client(session, client)
    return success()
