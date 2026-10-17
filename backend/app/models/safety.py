from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JsonB, sql_enum
from app.models.enums import ActionKind, ActionStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PendingAction(TimestampMixin, Base):
    """A proposal from the agent. Nothing moves until a human approves it."""

    __tablename__ = "pending_actions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[ActionKind] = mapped_column(sql_enum(ActionKind))
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonB)
    rationale: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[ActionStatus] = mapped_column(
        sql_enum(ActionStatus), default=ActionStatus.PENDING, index=True
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JsonB, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)

    owner: Mapped[User] = relationship(back_populates="pending_actions")


class AuditLog(Base):
    """Append-only trail of every proposal, approval and execution."""

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    data: Mapped[dict[str, Any] | None] = mapped_column(JsonB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="audit_logs")
