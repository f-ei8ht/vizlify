from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Client
from app.schemas.client import ClientCreate, ClientUpdate


async def list_clients(session: AsyncSession, owner_id: UUID) -> list[Client]:
    result = await session.scalars(
        select(Client).where(Client.owner_id == owner_id).order_by(Client.name)
    )
    return list(result)


async def get_client(session: AsyncSession, client_id: UUID, owner_id: UUID) -> Client:
    client = await session.scalar(
        select(Client).where(Client.id == client_id, Client.owner_id == owner_id)
    )
    if client is None:
        raise NotFoundError("Client")
    return client


async def create_client(session: AsyncSession, owner_id: UUID, data: ClientCreate) -> Client:
    client = Client(owner_id=owner_id, **data.model_dump())
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def update_client(session: AsyncSession, client: Client, data: ClientUpdate) -> Client:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await session.commit()
    await session.refresh(client)
    return client


async def delete_client(session: AsyncSession, client: Client) -> None:
    await session.delete(client)
    await session.commit()
