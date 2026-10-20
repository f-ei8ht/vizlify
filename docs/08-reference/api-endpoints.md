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

## Approvals

| Method | Path | Status | Body |
|--------|------|--------|------|
| `GET` | `/actions` | Implemented | Optional `?status=pending` |
| `GET` | `/actions/{id}` | Implemented | — |
| `POST` | `/actions/{id}/approve` | Implemented | — (`409` if already decided) |
| `POST` | `/actions/{id}/reject` | Implemented | `reason` |

Approving runs the executor once. The response carries `status: executed` and
a `result` with the PayPal ids. A failed execution leaves the proposal `failed`
and returns the underlying error (`409` for business conflicts, `502` for
PayPal failures).

## Invoices

| Method | Path | Status | Body |
|--------|------|--------|------|
| `POST` | `/milestones/{id}/invoice` | Implemented | — (creates a proposal) |
| `GET` | `/invoices` | Implemented | — |
| `GET` | `/invoices/{id}` | Implemented | — |
| `POST` | `/invoices/{id}/remind` | Implemented | — (creates a proposal) |
| `POST` | `/invoices/{id}/cancel` | Implemented | — (creates a proposal) |
| `POST` | `/invoices/{id}/payout` | Implemented | — (creates a proposal) |
| `POST` | `/invoices/{id}/refresh` | Implemented | — (pulls live status) |

Marking a milestone `done` creates the same invoice proposal automatically.
Creation and sending happen in one approved action.

## Payouts

| Method | Path | Status | Body |
|--------|------|--------|------|
| `GET` | `/payouts` | Implemented | — |
| `GET` | `/payouts/{id}` | Implemented | — |
| `POST` | `/payouts/{id}/execute` | Implemented | — (creates a proposal) |

A payout is prepared from a paid invoice (proposal, then approval). Execution is
a second proposal, enforced against the per-action and per-day spend caps.

## Webhooks

| Method | Path | Status | Body |
|--------|------|--------|------|
| `POST` | `/webhooks/paypal` | Implemented | PayPal event |

No auth header. In `sandbox`/`live` the signature is verified with
`PAYPAL_WEBHOOK_ID`; `mock` skips it. Events dedupe on PayPal's event id and
return `{"status":"processed"}` or `{"status":"duplicate"}`.

## Planned agent routes

| Method | Path | Purpose |
|--------|------|---------|
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
