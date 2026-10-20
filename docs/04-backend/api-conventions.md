# API conventions

> [Handbook index](../README.md) · [Part 4](./README.md) · **Status: Implemented**

The API is intentionally boring: one base URL, one response envelope, one error
shape, one authentication header.

## Base URL and docs

| Environment | Base URL |
|-------------|----------|
| Local (Docker) | `http://localhost:8000` |
| Local (uvicorn) | `http://localhost:8000` |
| Swagger UI | `/docs` |
| OpenAPI JSON | `/openapi.json` |

## The envelope

Every response — success or failure — is:

```json
{
  "data": { "…": "…" },
  "error": null
}
```

On failure:

```json
{
  "data": null,
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      { "field": "body.amount", "message": "Input should be greater than 0", "type": "greater_than" }
    ]
  }
}
```

HTTP status remains the source of truth. The body never duplicates it. The
frontend unwraps `data` and throws a typed `ApiError` when `error` is present;
see [API client](../05-frontend/api-client.md).

## Status codes

| Status | When |
|--------|------|
| `200` | Read or update succeeded |
| `201` | Resource created |
| `204` | No content *(reserved for webhook and PayPal acknowledgements)* |
| `400` | Bad request |
| `401` | Missing or invalid session |
| `403` | Permission denied on a visible resource |
| `404` | Missing resource, including cross-owner access |
| `409` | State conflict, for example team shares over 100% |
| `422` | Pydantic validation failure |
| `429` | Rate limited |
| `500` | Unexpected server error |
| `502` | PayPal or another upstream integration failed |

The last one is new with the PayPal client: `integration_error` means Vizlify
was reachable but PayPal was not, or rejected the call. The envelope carries
PayPal's `debug_id` so support can trace it.

## Error codes

| `error.code` | HTTP | Meaning |
|--------------|------|---------|
| `bad_request` | 400 | Malformed request |
| `unauthorized` | 401 | No valid session |
| `forbidden` | 403 | Not allowed for this user |
| `not_found` | 404 | Missing, or not owned by the caller |
| `conflict` | 409 | Business-rule conflict |
| `validation_error` | 422 | Field-level validation failure |
| `rate_limited` | 429 | Too many requests |
| `integration_error` | 502 | Upstream service failed |
| `internal_error` | 500 | Unhandled exception |

See [Error codes](../08-reference/error-codes.md) for the mapping to Python
exceptions.

## Authentication header

```http
Authorization: Bearer <clerk-session-token>
```

In `AUTH_MODE=dev` the header is ignored and the seeded user is resolved. In
`AUTH_MODE=clerk` a missing or invalid token returns `401` with a
`WWW-Authenticate: Bearer` header.

## Data types on the wire

| Type | JSON representation | Example |
|------|---------------------|---------|
| UUID | string | `"8afb5478-e8ae-457a-93d0-8e45b8409b01"` |
| Money | **string**, two decimals | `"2500.00"` |
| Percentage | string, two decimals | `"40.00"` |
| Date | ISO 8601 date | `"2026-11-03"` |
| Timestamp | ISO 8601 with timezone | `"2026-10-20T18:04:00Z"` |
| Enum | lowercase string | `"friendly"`, `"todo"` |

Money is a string on purpose. JavaScript numbers are IEEE-754 doubles; `0.1 +
0.2` is not `0.3`, and a cent lost in a payout is a real bug. The frontend
converts only for display via `formatMoney`.

## Validation

Pydantic validates at the boundary. Details are flattened to one entry per
problem:

```json
{
  "field": "body.email",
  "message": "value is not a valid email address: An email address must have an @-sign.",
  "type": "value_error"
}
```

The frontend exposes `ApiError.fieldErrors` as a `field → message` map for form
display.

## Versioning and pagination

There is no `/v1` prefix yet and no pagination. Both are deliberate
simplifications for the hackathon; the roadmap (E16) tracks versioning and a
typed SDK. List endpoints return arrays ordered deterministically:

| Endpoint | Order |
|----------|-------|
| `/clients` | name |
| `/projects` | name |
| `/projects/{id}/milestones` | due date |
| `/projects/{id}/team` | name |

## Idempotency

Reads are naturally idempotent. Writes are not yet idempotent at the HTTP layer,
but every PayPal write carries a deterministic `PayPal-Request-Id`, so a retried
approval cannot create a duplicate invoice or payout. The approval executor
(planned) will make the HTTP side idempotent too, returning `409` on a second
approval of the same proposal.

Next: [Authentication](./authentication.md) →
