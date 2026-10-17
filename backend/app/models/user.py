from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.brief import Brief
    from app.models.chat import ChatMessage
    from app.models.client import Client
    from app.models.project import Project
    from app.models.safety import AuditLog, PendingAction


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    clerk_user_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, default=None
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    business_name: Mapped[str | None] = mapped_column(String(255), default=None)
    paypal_email: Mapped[str | None] = mapped_column(String(320), default=None)

    clients: Mapped[list[Client]] = relationship(back_populates="owner")
    projects: Mapped[list[Project]] = relationship(back_populates="owner")
    briefs: Mapped[list[Brief]] = relationship(back_populates="owner")
    pending_actions: Mapped[list[PendingAction]] = relationship(back_populates="owner")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")
    chat_messages: Mapped[list[ChatMessage]] = relationship(back_populates="user")
