# Product and scope

> [Handbook index](../README.md) · [Part 1](./README.md) · **Status: living document**

This chapter is the truth about what Vizlify does today. It is deliberately
conservative: a feature is only **Implemented** when code and tests exist.

## What works today

| Capability | Where | Evidence |
|------------|-------|----------|
| One-command local stack | `compose.yaml` | `db`, `api`, `web` start with health checks |
| Clerk authentication | `backend/app/auth/` | Signed-in users map to local `users` rows |
| Key-free local mode | `AUTH_MODE=dev` | Seeded demo user, refused in production |
| Clients CRUD | `/clients` | Owner-scoped, 8 tests |
| Projects CRUD | `/projects` | Owner-scoped, 4 tests |
| Milestones CRUD | `/projects/{id}/milestones` | Owner-scoped, 5 tests |
| Team members and splits | `/projects/{id}/team` | Shares cannot exceed 100%, 3 tests |
| Full database schema | Alembic | All 12 tables from the roadmap data model |
| Demo agency seed | `python -m app.scripts.seed` | Idempotent, validated JSON fixture |
| PayPal transport | `backend/app/paypal/` | OAuth cache, retries, idempotency, mock mode, 33 tests |
| Frontend API layer | `frontend/lib/api/` | Envelope-aware client, typed errors, query hooks |
| Frontend providers | `frontend/components/providers/` | Clerk, theme, TanStack Query, API client |

The backend suite is **78 tests** with roughly **96% statement coverage**
(`cd backend && uv run pytest`).

## What is scaffolded

| Area | What exists | What is missing |
|------|-------------|-----------------|
| Next.js UI | App Router shell, layout, providers, buttons, states | Real screens: dashboard, clients, projects, invoices, approvals, chat |
| Demo mode | Seed script, `DEMO_MODE` flag, `LLM_MODE=mock` | Time travel, reset button, judge walkthrough |
| Safety core | `pending_actions` and `audit_log` tables | Proposal service, approve/reject endpoints, executor, spend caps |
| Billing data | `invoices`, `payouts`, `payout_items` tables and enums | Endpoints, UI, webhook handlers, split calculation |
| API docs | FastAPI's `/docs` and `/openapi.json` | A generated typed frontend SDK |

## What is planned

The roadmap defines sixteen epics. This table tracks them at a glance; the
authoritative, day-by-day plan is in [ROADMAP.md](../../ROADMAP.md).

| Epic | Area | Status | Notes |
|------|------|--------|-------|
| E1 | Platform foundation | **Implemented** | Compose, config, auth, errors, seed |
| E2 | Clients, projects, milestones, team | **Implemented** | Payment-behaviour score and timelines are not |
| E3 | AI scope from a brief | **Planned** | Needs LLM client, structured output, eval harness |
| E4 | Invoicing | **Planned** | Transport ready; no invoice service or routes |
| E5 | Payments and webhooks | **Planned** | Signature verification and event store are next |
| E6 | Payouts and splits | **Planned** | Split maths, batches, item statuses |
| E7 | Approval queue and executor | **Planned** | The safety core; tables already exist |
| E8 | Collections and nudge-bot | **Planned** | Overdue sweep, tone-aware drafts |
| E9 | Disputes | **Planned** | Ingest, summarise, draft response |
| E10 | Finance chat and Studio agent | **Planned** | Tool calling, proposals, NL-to-widget |
| E11 | Dashboard (AG Studio) | **Planned** | Needs an AG Studio trial key |
| E12 | Notifications | **Planned** | In-app centre, email |
| E13 | Demo and judge mode | **Scaffolded** | Seed works; time travel and reset do not |
| E14 | Reconciliation and reporting | **Planned** | Nightly reconcile, statements |
| E15 | Agentic commerce and interoperability | **Planned** | MCP server, outbound webhooks, API keys |
| E16 | API and documentation | **Scaffolded** | OpenAPI is live; this handbook is the docs portal; SDK is planned |

## The money loop

The product is one loop. Solid arrows exist today; dashed arrows do not.

```mermaid
flowchart LR
    Brief["Brief"] -->|"drafted by agent"| Scope["Scope + milestones"]
    Scope -->|"approved"| Draft["Draft invoice"]
    Draft -->|"sent"| Invoice["PayPal invoice"]
    Invoice -->|"paid webhook"| Paid["Paid"]
    Paid -->|"split proposed"| Payout["Payout batch"]
    Payout -->|"approved"| Sent["Money sent"]
    Invoice -.->|"overdue"| Nudge["Reminder proposal"]

    classDef done fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef todo fill:#fef9c3,stroke:#ca8a04,color:#713f12
    class Brief,Scope,Draft,Invoice,Paid,Payout,Sent,Nudge todo
```

Status at the time of writing: the **heavy rectangle** of this loop — approval
queue, invoice creation, webhooks, payout execution — is not yet exposed. The
PayPal transport and the database schema beneath it are ready, which is why the
next milestone is the executor plus invoicing (see
[Project status](../09-project/status-and-roadmap.md)).

## Scope discipline

The hackathon plan uses tiers: **P0 must**, **P1 should**, **P2 stretch**. When
time runs short, P2 is cut first, then P1. No P0 is cut, because each one
appears in the three-minute demo.

The same rule applies to documentation: a page that describes a P0 incorrectly
is a worse bug than a missing P2 page.

Next: [Tech stack](./tech-stack.md) →
