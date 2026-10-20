from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import PayoutItemStatus, PayoutStatus


class PayoutItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_member_id: UUID
    paypal_item_id: str | None = None
    amount: Decimal
    status: PayoutItemStatus


class PayoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    paypal_batch_id: str | None = None
    status: PayoutStatus
    total: Decimal
    currency: str
    created_at: datetime
    items: list[PayoutItemRead]
