from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import InvoiceStatus


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    milestone_id: UUID
    paypal_invoice_id: str | None = None
    number: str | None = None
    amount: Decimal
    currency: str
    status: InvoiceStatus
    due_date: date | None = None
    paid_at: datetime | None = None
