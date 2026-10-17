from enum import StrEnum


class TonePreference(StrEnum):
    FRIENDLY = "friendly"
    FORMAL = "formal"
    FIRM = "firm"


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class BriefStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class MilestoneStatus(StrEnum):
    TODO = "todo"
    DONE = "done"
    BILLED = "billed"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PayoutStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    DENIED = "denied"
    UNCLAIMED = "unclaimed"
    FAILED = "failed"


class PayoutItemStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    DENIED = "denied"
    UNCLAIMED = "unclaimed"
    FAILED = "failed"


class ActionStatus(StrEnum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionKind(StrEnum):
    CREATE_INVOICE = "create_invoice"
    SEND_INVOICE = "send_invoice"
    SEND_REMINDER = "send_reminder"
    CANCEL_INVOICE = "cancel_invoice"
    PREPARE_PAYOUT = "prepare_payout"
    EXECUTE_PAYOUT = "execute_payout"
    DRAFT_DISPUTE_RESPONSE = "draft_dispute_response"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
