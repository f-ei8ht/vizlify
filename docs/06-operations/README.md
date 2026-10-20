# Part 6 — Operations

> [Handbook index](../README.md) · **Part 6 of 9**

How Vizlify runs locally, how it is meant to run in production, and what keeps
the money safe along the way.

## Chapters

1. [Docker](./docker.md) — the three-service local stack.
2. [Deployment](./deployment.md) — Render topology and go-live checklist.
3. [Security](./security.md) — controls, gaps and the sandbox guarantee.

## Environments

| Environment | Auth | PayPal | LLM | Data |
|-------------|------|--------|-----|------|
| Local | `dev` | `mock` or `sandbox` | `mock` | Seeded demo |
| CI | `dev` | `mock` | `mock` | SQLite in memory |
| Staging *(planned)* | Clerk test | `sandbox` | `mock` or live | Render Postgres |
| Production *(planned)* | Clerk | `sandbox` only for the hackathon | live | Render Postgres |

The rule: **no environment runs `PAYPAL_MODE=live`.** The mode exists so the
code is production-shaped, but the hackathon build is sandbox-only.

Next: [Docker](./docker.md) →
