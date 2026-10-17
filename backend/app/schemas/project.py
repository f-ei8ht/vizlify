from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProjectStatus


class ProjectCreate(BaseModel):
    client_id: UUID
    name: str = Field(min_length=1, max_length=255)
    currency: str = Field(min_length=3, max_length=3)
    status: ProjectStatus = ProjectStatus.ACTIVE


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: ProjectStatus | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    name: str
    currency: str
    status: ProjectStatus
