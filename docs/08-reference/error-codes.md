# Error codes

> [Handbook index](../README.md) · [Part 8](./README.md) · **Status: Implemented**

## Envelope

```json
{
  "data": null,
  "error": {
    "code": "conflict",
    "message": "Team shares cannot exceed 100%.",
    "details": null
  }
}
```

`error.code` is stable. `error.message` is safe to show to a user.
`error.details` is present for validation errors and PayPal `debug_id`s.

## Codes

| Code | HTTP | Python | Raised when |
|------|------|--------|-------------|
| `bad_request` | 400 | `AppError` | A request is malformed outside Pydantic's checks |
| `unauthorized` | 401 | `HTTPException(401)` | No session, invalid token, or demo workspace missing |
| `forbidden` | 403 | `AppError` subclass | Authenticated but not allowed on a visible resource |
| `not_found` | 404 | `NotFoundError` | Missing resource, including a foreign owner's row |
| `conflict` | 409 | `ConflictError` | State conflict such as team shares over 100% |
| `validation_error` | 422 | `RequestValidationError` | Pydantic rejected a field |
| `rate_limited` | 429 | `AppError` | Too many requests *(not enforced yet)* |
| `integration_error` | 502 | `PayPalError` | PayPal unreachable, rejected, or throttled |
| `internal_error` | 500 | unhandled `Exception` | A bug; the message is generic |

## Validation details

```json
{
  "code": "validation_error",
  "message": "Request validation failed.",
  "details": [
    {
      "field": "body.amount",
      "message": "Input should be greater than 0",
      "type": "greater_than"
    }
  ]
}
```

- `field` is a dotted path (`body`, `path`, `query`).
- `type` is Pydantic's error type, useful for tests but not for copy.
- The frontend flattens these into `ApiError.fieldErrors`.

## Integration errors

PayPal failures keep PayPal's stable name and `debug_id`:

```json
{
  "code": "integration_error",
  "message": "PayPal rejected the request.",
  "details": [
    { "field": "paypal_error", "message": "UNPROCESSABLE_ENTITY" },
    { "field": "debug_id", "message": "abc123def456" }
  ]
}
```

| PayPal status | Message shown |
|---------------|---------------|
| 401 | PayPal rejected the API credentials. |
| 403 | PayPal denied this request. Check the app's enabled features. |
| 429 | PayPal is rate limiting requests. Try again shortly. |
| 5xx | PayPal is temporarily unavailable. Try again shortly. |
| other 4xx | PayPal rejected the request. |

The raw PayPal body is logged, never returned. `debug_id` is the identifier to
quote to PayPal support.

## Internal errors

`internal_error` deliberately hides the exception. The full traceback goes to
the server log. If a user reports a 500, ask for the timestamp and route, then
match it against the log; do not ask them to reproduce with credentials.

## Mapping in code

```python
from app.core.errors import AppError, ConflictError, NotFoundError

raise NotFoundError("Client")          # 404, "Client not found."
raise ConflictError("Shares exceed 100%.")  # 409
```

Custom exceptions subclass `AppError` and set `code`. The handlers in
`app/core/errors.py` are registered once in `create_app()`.

Next: [Glossary](./glossary.md) →
