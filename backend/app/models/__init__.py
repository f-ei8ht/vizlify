"""Import every model so SQLAlchemy's metadata and Alembic autogenerate see them."""

from app.models.billing import Invoice, Payout, PayoutItem
from app.models.brief import Brief
from app.models.chat import ChatMessage
from app.models.client import Client
from app.models.enums import (
    ActionKind,
    ActionStatus,
    BriefStatus,
    ChatRole,
    InvoiceStatus,
    MilestoneStatus,
    PayoutItemStatus,
    PayoutStatus,
    ProjectStatus,
    TonePreference,
)
from app.models.integration import WebhookEvent
from app.models.project import Milestone, Project, TeamMember
from app.models.safety import AuditLog, PendingAction
from app.models.user import User

__all__ = [
    "ActionKind",
    "ActionStatus",
    "AuditLog",
    "Brief",
    "BriefStatus",
    "ChatMessage",
    "ChatRole",
    "Client",
    "Invoice",
    "InvoiceStatus",
    "Milestone",
    "MilestoneStatus",
    "Payout",
    "PayoutItem",
    "PayoutItemStatus",
    "PayoutStatus",
    "PendingAction",
    "Project",
    "ProjectStatus",
    "TeamMember",
    "TonePreference",
    "User",
    "WebhookEvent",
]
