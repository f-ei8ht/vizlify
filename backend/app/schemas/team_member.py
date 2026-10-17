from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TeamMemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    paypal_email: EmailStr
    share_percent: Decimal = Field(gt=0, le=100, max_digits=5, decimal_places=2)


class TeamMemberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    paypal_email: EmailStr | None = None
    share_percent: Decimal | None = Field(
        default=None, gt=0, le=100, max_digits=5, decimal_places=2
    )


class TeamMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    paypal_email: EmailStr
    share_percent: Decimal
