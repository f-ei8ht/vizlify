from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, sql_enum
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.billing import Invoice
    from app.models.client import Client
    from app.models.user import User

MONEY = Numeric(12, 2)
SHARE = Numeric(5, 2)


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[ProjectStatus] = mapped_column(
        sql_enum(ProjectStatus), default=ProjectStatus.ACTIVE
    )

    owner: Mapped[User] = relationship(back_populates="projects")
    client: Mapped[Client] = relationship(back_populates="projects")
    milestones: Mapped[list[Milestone]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    team_members: Mapped[list[TeamMember]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Milestone(TimestampMixin, Base):
    __tablename__ = "milestones"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    due_date: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[MilestoneStatus] = mapped_column(
        sql_enum(MilestoneStatus), default=MilestoneStatus.TODO
    )

    project: Mapped[Project] = relationship(back_populates="milestones")
    invoice: Mapped[Invoice | None] = relationship(back_populates="milestone", uselist=False)


class TeamMember(TimestampMixin, Base):
    __tablename__ = "team_members"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    paypal_email: Mapped[str] = mapped_column(String(320))
    share_percent: Mapped[Decimal] = mapped_column(SHARE)

    project: Mapped[Project] = relationship(back_populates="team_members")
