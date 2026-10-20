# API endpoints

> [Handbook index](../README.md) · [Part 8](./README.md) · **Status: Implemented and Planned**

Base URL: `http://localhost:8000`. Every route except `/`, `/health` and
`/openapi.json` requires authentication.

**Implemented** routes are live today. **Planned** routes are the agreed shape
and are not registered yet.

## System

| Method | Path | Auth | Status | Returns |
|--------|------|------|--------|---------|
| `GET` | `/` | no | Implemented | API name, version, docs link |
| `GET` | `/health` | no | Implemented | `{"status":"ok"}` |
| `GET` | `/docs` | no | Implemented | Swagger UI |
| `GET` | `/openapi.json` | no | Implemented | OpenAPI schema |

## Account

| Method | Path | Auth | Status | Body / returns |
|--------|------|------|--------|----------------|
| `GET` | `/me` | yes | Implemented | Current user |
| `PATCH` | `/me` | yes | Planned | Update business name, PayPal email |
| `GET` | `/me/export` | yes | Planned | Data export |
| `DELETE` | `/me` | yes | Planned | Account deletion |

## Clients

| Method | Path | Status | Body |
|--------|------|--------|------|
| `GET` | `/clients` | Implemented | — |
| `POST` | `/clients` | Implemented | `name`, `email`, `tone_preference?` |
| `GET` | `/clients/{id}` | Implemented | — |
| `PATCH` | `/clients/{id}` | Implemented | any create field |
| `DELETE` | `/clients/{id}` | Implemented | — |
| `GET` | `/clients/{id}/timeline` | Planned | — |

Validation:

| Field | Rule |
|-------|------|
| `name` | 1–255 characters |
| `email` | valid email, 1–320 characters |
| `tone_preference` | `friendly`, `formal`, `firm` |

Deleting a client cascades its projects, milestones and team members.

## Projects

| Method | Path | Status | Body |
|--------|------|--------|------|
| `GET` | `/projects` | Implemented | — |
| `POST` | `/projects` | Implemented | `client_id`, `name`, `currency`, `status?` |
| `GET` | `/projects/{id}` | Implemented | — |
| `PATCH` | `/projects/{id}` | Implemented | `name`, `currency`, `status` |
| `DELETE` | `/projects/{id}` | Implemented | — |

Validation:

| Field | Rule |
|-------|------|
| `client_id` | must exist and belong to the caller |
| `name` | 1–255 characters |
| `currency` | exactly 3 characters |
| `status` | `active`, `completed`, `archived` |

## Milestones

| Method | Path | Status | Body |
|--------|------|--------|------|
| `GET` | `/projects/{project_id}/milestones` | Implemented | — |
| `POST` | `/projects/{project_id}/milestones` | Implemented | `title`, `amount`, `due_date?`, `status?` |
| `GET` | `/milestones/{id}` | Implemented | — |
| `PATCH` | `/milestones/{id}` | Implemented | any create field |
| `DELETE` | `/milestones/{id}` | Implemented | — |

Validation:

| Field | Rule |
|-------|------|
| `title` | 1–255 characters |
| `amount` | `> 0`, up to 12 digits, 2 decimals |
| `due_date` | ISO date or `null` |
| `status` | `todo`, `done`, `billed` |

## Team members

| Method | Path | Status | Body |
|--------|------|--------|------|
| `GET` | `/projects/{project_id}/team` | Implemented | — |
| `POST` | `/projects/{project_id}/team` | Implemented | `name`, `paypal_email`, `share_percent` |
| `PATCH` | `/team/{id}` | Implemented | any create field |
| `DELETE` | `/team/{id}` | Implemented | — |

Validation:

| Field | Rule |
|-------|------|
| `name` | 1–255 characters |
| `paypal_email` | valid email |
| `share_percent` | `> 0`, `<= 100`, 2 decimals |
| project total | sum of shares `<= 100`, otherwise `409` |

## Planned money routes

| Method | Path | Body | Notes |
|--------|------|------|-------|
| `POST` | `/milestones/{id}/invoice` | — | Creates an invoice proposal |
| `GET` | `/invoices` | — | List with live status |
| `GET` | `/invoices/{id}` | — | Detail plus PayPal link |
| `POST` | `/invoices/{id}/send` | — | Executes an approved action |
| `POST` | `/invoices/{id}/remind` | `tone?` | Sends via PayPal |
| `POST` | `/invoices/{id}/cancel` | `reason?` | Cancels locally and at PayPal |
| `POST` | `/invoices/{id}/refresh` | — | Pulls live state from PayPal |
| `GET` | `/payouts` | — | List |
| `GET` | `/payouts/{id}` | — | Batch and item statuses |
| `POST` | `/payouts/{id}/execute` | — | Executes an approved payout |
| `POST` | `/webhooks/paypal` | PayPal event | Signature-verified, idempotent |

## Planned agent routes

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/actions` | Approval queue with rationale |
| `POST` | `/actions/{id}/approve` | Idempotent; `409` on double approve |
| `POST` | `/actions/{id}/reject` | Requires a reason |
| `POST` | `/briefs` | Start scope extraction |
| `GET` | `/briefs/{id}` | Poll status and result |
| `POST` | `/chat` | Tool-calling chat; writes become proposals |
| `GET` | `/analytics/*` | Dashboard widgets |
| `POST` | `/demo/time-travel` | Demo-only overdue simulation |
| `POST` | `/demo/reset` | Restore seed data |

## Conventions for every route

- Success: `{ "data": …, "error": null }`.
- Failure: `{ "data": null, "error": { code, message, details? } }`.
- IDs are UUID strings; money is a decimal string.
- List order is deterministic (see
  [API conventions](../04-backend/api-conventions.md#versioning-and-pagination)).
- Unknown ids and foreign ids both return `404`.

Next: [Error codes](./error-codes.md) →
