from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, sql_enum
from app.models.enums import InvoiceStatus, PayoutItemStatus, PayoutStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Milestone, TeamMember

MONEY = Numeric(12, 2)


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    milestone_id: Mapped[UUID] = mapped_column(
        ForeignKey("milestones.id", ondelete="CASCADE"), index=True
    )
    paypal_invoice_id: Mapped[str | None] = mapped_column(String(255), default=None)
    number: Mapped[str | None] = mapped_column(String(64), default=None)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[InvoiceStatus] = mapped_column(
        sql_enum(InvoiceStatus), default=InvoiceStatus.DRAFT
    )
    due_date: Mapped[date | None] = mapped_column(Date, default=None)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    milestone: Mapped[Milestone] = relationship(back_populates="invoice")
    payouts: Mapped[list[Payout]] = relationship(back_populates="invoice")


class Payout(TimestampMixin, Base):
    __tablename__ = "payouts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    paypal_batch_id: Mapped[str | None] = mapped_column(String(255), default=None)
    status: Mapped[PayoutStatus] = mapped_column(
        sql_enum(PayoutStatus), default=PayoutStatus.PENDING
    )
    total: Mapped[Decimal] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    invoice: Mapped[Invoice] = relationship(back_populates="payouts")
    items: Mapped[list[PayoutItem]] = relationship(
        back_populates="payout", cascade="all, delete-orphan"
    )


class PayoutItem(TimestampMixin, Base):
    __tablename__ = "payout_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    payout_id: Mapped[UUID] = mapped_column(
        ForeignKey("payouts.id", ondelete="CASCADE"), index=True
    )
    team_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("team_members.id", ondelete="CASCADE"), index=True
    )
    paypal_item_id: Mapped[str | None] = mapped_column(String(255), default=None, index=True)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    status: Mapped[PayoutItemStatus] = mapped_column(
        sql_enum(PayoutItemStatus), default=PayoutItemStatus.PENDING
    )

    payout: Mapped[Payout] = relationship(back_populates="items")
    team_member: Mapped[TeamMember] = relationship()
