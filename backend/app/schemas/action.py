from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActionKind, ActionStatus


class ActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: ActionKind
    status: ActionStatus
    payload: dict[str, Any]
    rationale: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
