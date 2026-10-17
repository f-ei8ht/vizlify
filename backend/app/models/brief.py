from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JsonB, sql_enum
from app.models.enums import BriefStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Brief(TimestampMixin, Base):
    __tablename__ = "briefs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[BriefStatus] = mapped_column(sql_enum(BriefStatus), default=BriefStatus.PENDING)
    result: Mapped[dict[str, Any] | None] = mapped_column(JsonB, default=None)

    owner: Mapped[User] = relationship(back_populates="briefs")
