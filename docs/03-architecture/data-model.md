# Data model

> [Handbook index](../README.md) · [Part 3](./README.md) · **Status: Implemented**

All tables below exist in the database, and the invoice, payout, approval and
webhook **routes** are implemented. The UI on top is still being built.

## Entity relationships

```mermaid
erDiagram
    USER ||--o{ CLIENT : owns
    USER ||--o{ PROJECT : owns
    USER ||--o{ BRIEF : owns
    USER ||--o{ PENDING_ACTION : proposes
    USER ||--o{ AUDIT_LOG : generates
    USER ||--o{ CHAT_MESSAGE : writes
    CLIENT ||--o{ PROJECT : has
    PROJECT ||--o{ MILESTONE : has
    PROJECT ||--o{ TEAM_MEMBER : has
    MILESTONE ||--o| INVOICE : billed_by
    INVOICE ||--o{ PAYOUT : funds
    PAYOUT ||--o{ PAYOUT_ITEM : contains
    TEAM_MEMBER ||--o{ PAYOUT_ITEM : receives

    USER {
        uuid id PK
        string clerk_user_id
        string email
        string password_hash
        string business_name
        string paypal_email
    }
    CLIENT {
        uuid id PK
        uuid owner_id FK
        string name
        string email
        enum tone_preference
    }
    PROJECT {
        uuid id PK
        uuid owner_id FK
        uuid client_id FK
        string name
        string currency
        enum status
    }
    MILESTONE {
        uuid id PK
        uuid project_id FK
        string title
        numeric amount
        date due_date
        enum status
    }
    TEAM_MEMBER {
        uuid id PK
        uuid project_id FK
        string name
        string paypal_email
        numeric share_percent
    }
    INVOICE {
        uuid id PK
        uuid milestone_id FK
        string paypal_invoice_id
        string number
        numeric amount
        string currency
        enum status
        date due_date
        timestamp paid_at
    }
    PAYOUT {
        uuid id PK
        uuid invoice_id FK
        string paypal_batch_id
        enum status
        numeric total
        string currency
    }
    PAYOUT_ITEM {
        uuid id PK
        uuid payout_id FK
        uuid team_member_id FK
        string paypal_item_id
        numeric amount
        enum status
    }
    PENDING_ACTION {
        uuid id PK
        uuid owner_id FK
        enum kind
        string dedupe_key
        jsonb payload
        text rationale
        enum status
        jsonb result
    }
    AUDIT_LOG {
        uuid id PK
        uuid user_id FK
        string action
        string entity
        string entity_id
        jsonb data
    }
    BRIEF {
        uuid id PK
        uuid owner_id FK
        text text
        enum status
        jsonb result
    }
    CHAT_MESSAGE {
        uuid id PK
        uuid user_id FK
        enum role
        text content
        jsonb tool_calls
    }
```

`WEBHOOK_EVENT` stands alone, keyed by PayPal's event id:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | string, primary key | PayPal event id; the dedupe key |
| `event_type` | string, indexed | For example `INVOICING.INVOICE.PAID` |
| `payload` | JSONB | Raw verified event |
| `processed_at` | timestamp | Set after handling; null means pending |
| `created_at` | timestamp | Receipt time |

## Enumerations

| Enum | Values |
|------|--------|
| `TonePreference` | `friendly`, `formal`, `firm` |
| `ProjectStatus` | `active`, `completed`, `archived` |
| `MilestoneStatus` | `todo`, `done`, `billed` |
| `InvoiceStatus` | `draft`, `sent`, `paid`, `partially_paid`, `cancelled`, `refunded` |
| `PayoutStatus` / `PayoutItemStatus` | `pending`, `success`, `denied`, `unclaimed`, `failed` |
| `ActionStatus` | `pending`, `executed`, `failed`, `rejected`, `expired` |
| `ActionKind` | `create_invoice`, `send_invoice`, `send_reminder`, `cancel_invoice`, `prepare_payout`, `execute_payout`, `draft_dispute_response` |
| `BriefStatus` | `pending`, `ready`, `failed` |
| `ChatRole` | `user`, `assistant`, `system`, `tool` |

Enums are persisted by **value** (lowercase), not member name, so the database
reads naturally and survives Python renames.

## Money rules

| Rule | Implementation |
|------|----------------|
| No floats | `Numeric(12, 2)` in the database, `Decimal` in Python |
| One currency per project | `projects.currency`; invoices and payouts copy it |
| Positive amounts | Milestone `amount > 0` at the schema boundary |
| Splits bounded | Team shares are `> 0` and never exceed 100% in total |
| Deterministic rounding *(planned)* | Largest-remainder allocation, so items always sum to the invoice total |

The split algorithm is not written yet. When it is, it will live in
`services/payouts.py` and be tested with amounts such as `100.00` split three
ways — the case where naive rounding loses a cent.

## Ownership and cascades

```mermaid
flowchart LR
    User -->|"owns"| Client -->|"has"| Project
    User -->|"owns"| Project
    Project -->|"delete cascade"| Milestone -->|"cascade"| Invoice -->|"cascade"| Payout -->|"cascade"| Item["Payout item"]
    Project -->|"cascade"| Team["Team member"]
    User -->|"delete cascade"| Action["Pending action"]
    User -->|"delete set null"| Audit["Audit log"]
```

Deleting an agency removes its business data but **keeps audit rows** with a
null user id. An audit trail that disappears with its author is not an audit
trail.

## Indexes

- Every owner foreign key is indexed (`users` scoping).
- `clients.email`, `users.email`, `users.clerk_user_id` are indexed; emails and
  Clerk ids are unique.
- `pending_actions.dedupe_key` is unique, which is what makes retries safe.
- `pending_actions.status` and `webhook_events.event_type` are indexed for
  queues and handlers.
- `audit_log.entity` + `entity_id` are indexed for "what happened to this
  invoice?" queries.

## Migrations

Four migrations exist:

| Revision | Change |
|----------|--------|
| `281c60b543e0` | Initial schema: all tables |
| `77a59e157cd9` | Add `users.clerk_user_id` |
| `a1dc76bf447b` | Make `users.business_name` nullable |
| `c3f1a9d2b7e4` | Add `payout_items.paypal_item_id` |

Never edit an applied migration. Add a new one (`alembic revision
--autogenerate -m "…"`) and review the generated file before committing.

Next: [API conventions](../04-backend/api-conventions.md) →
