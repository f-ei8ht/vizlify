from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, sql_enum
from app.models.enums import TonePreference
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class Client(TimestampMixin, Base):
    __tablename__ = "clients"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320))
    tone_preference: Mapped[TonePreference] = mapped_column(
        sql_enum(TonePreference), default=TonePreference.FRIENDLY
    )

    owner: Mapped[User] = relationship(back_populates="clients")
    projects: Mapped[list[Project]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
