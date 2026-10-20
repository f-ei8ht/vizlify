# System overview

> [Handbook index](../README.md) · [Part 3](./README.md) · **Status: Implemented (core), Planned (agent and billing routes)**

## Components

```mermaid
flowchart TB
    subgraph Browser["Browser"]
        direction TB
        Pages["Next.js App Router<br/>(screens: scaffolded)"]
        Hooks["TanStack Query hooks<br/>lib/api/*"]
        Client["API client<br/>envelope + Bearer token"]
        Pages --> Hooks --> Client
    end

    subgraph Web["Next.js server"]
        Proxy["proxy.ts<br/>Clerk middleware"]
        Shell["layout + providers"]
    end

    subgraph API["FastAPI"]
        direction TB
        Routers["api/*<br/>HTTP shape"]
        Services["services/*<br/>rules + queries"]
        Models["models/*<br/>SQLAlchemy"]
        AuthDep["auth/deps.py<br/>CurrentUser"]
        PaypalClient["paypal/client.py<br/>token cache + retries"]
        Routers --> Services --> Models
        Routers --> AuthDep
    end

    subgraph Data["PostgreSQL 16"]
        Tables[("users · clients · projects<br/>milestones · team_members<br/>invoices · payouts · pending_actions<br/>audit_log · webhook_events · briefs · chat")]
    end

    subgraph External["External"]
        Clerk["Clerk"]
        PayPal["PayPal REST"]
        Cerebras["Cerebras<br/>(planned)"]
    end

    Client -->|"fetch + JSON"| Routers
    Shell --> Proxy --> Clerk
    AuthDep -->|"verify session"| Clerk
    Models --> Tables
    Services --> PaypalClient --> PayPal

    classDef planned stroke-dasharray: 5 5
    class Cerebras planned
```

## Responsibilities

| Component | Owns | Must never |
|-----------|------|------------|
| Next.js | Rendering, routing, session UI, optimistic cache | Talk to PayPal or Postgres directly |
| FastAPI routers | HTTP status, validation, dependency wiring | Contain money rules |
| Services | Ownership checks, transactions, split maths | Know about HTTP |
| Models | Schema and relationships | Call external services |
| PayPal client | OAuth, retries, idempotency, error translation | Decide whether an action is approved |
| Approval executor *(planned)* | Execute only approved proposals | Be callable by the agent |
| Clerk | Sessions and identity | Store agency business data |

## Runtime topology (local)

```mermaid
flowchart LR
    Dev["Developer"] -->|"localhost:3000"| Web["web<br/>Next.js 16"]
    Dev -->|"localhost:8000"| APIC["api<br/>FastAPI"]
    Web -->|"http://api:8000"| APIC
    APIC -->|"postgresql+asyncpg"| DB[("db<br/>PostgreSQL 16")]
    APIC -.->|"sandbox only when configured"| PayPal["PayPal sandbox"]
```

## Planned additions

The architecture is designed so these can be added without moving boundaries:

| Addition | Where it plugs in | Status |
|----------|-------------------|--------|
| Invoice and payout routes | `api/invoices.py`, `api/payouts.py` → existing services | Planned |
| Approval queue and executor | `api/actions.py`, `services/executor.py` → `pending_actions` | Planned |
| Webhook receiver | `api/webhooks.py` → `webhook_events`, signature verifier | Planned |
| LLM client and tools | `app/ai/` → proposals only | Planned |
| Render Workflows | `workflows/` → same services | Planned |
| AG Studio dashboard | `components/studio/` behind a flag | Planned |

## Why this shape

- **One API, two clients.** The browser and (later) the MCP server use the same
  routes, so the safety rules cannot be bypassed by a second entry point.
- **Postgres is the queue.** `pending_actions` is a table, not an in-memory
  queue, so a crash cannot lose a proposal or approve one twice.
- **PayPal is the ledger of record.** Local invoice and payout rows mirror it;
  webhooks reconcile drift.
- **Modes, not branches.** Dev, mock and sandbox are selected at startup, not
  scattered through request code.

Next: [Request lifecycle](./request-lifecycle.md) →
