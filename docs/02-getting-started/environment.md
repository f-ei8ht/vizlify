# Environment

> [Handbook index](../README.md) · [Part 2](./README.md) · **Status: Implemented**

Every configuration value comes from the environment. `backend/.env.example`
is the template; `backend/.env` is what Docker Compose reads when present.

There are three independent modes. Each has a safe local default and at least
one fail-closed rule.

```mermaid
flowchart LR
    Auth{"AUTH_MODE"} -->|dev| Dev["Seeded demo user<br/>no keys<br/>blocked in production"]
    Auth -->|clerk| Clerk["Clerk session token<br/>requires secret + parties"]

    LLM{"LLM_MODE"} -->|mock| MockLLM["Deterministic output<br/>no key"]
    LLM -->|live| LiveLLM["Cerebras API<br/>planned"]

    PP{"PAYPAL_MODE"} -->|mock| MockPP["In-process fake<br/>no keys<br/>blocked in production"]
    PP -->|sandbox| Sandbox["api-m.sandbox.paypal.com<br/>requires credentials"]
    PP -->|live| LivePP["api-m.paypal.com<br/>production only"]
```

## Backend variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | yes | — | `development`, `test`, or `production` |
| `SECRET_KEY` | yes | — | Application secret; use a long random string |
| `DATABASE_URL` | yes | — | SQLAlchemy async URL (`postgresql+asyncpg://…`) |
| `CORS_ORIGINS` | yes | — | Comma-separated allowed origins |
| `FRONTEND_URL` | yes | — | Base URL of the web app |
| `AUTH_MODE` | yes | — | `dev` or `clerk` |
| `DEV_USER_EMAIL` | in `dev` | — | The seeded demo account |
| `CLERK_SECRET_KEY` | in `clerk` | — | Clerk backend secret |
| `CLERK_JWT_KEY` | in `clerk` | — | Clerk PEM public key for networkless verification |
| `CLERK_AUTHORIZED_PARTIES` | in `clerk` | — | Allowed origins for session tokens |
| `PAYPAL_MODE` | no | `mock` | `mock`, `sandbox`, or `live` |
| `PAYPAL_CLIENT_ID` | unless mock | — | PayPal app client id |
| `PAYPAL_CLIENT_SECRET` | unless mock | — | PayPal app secret |
| `PAYPAL_WEBHOOK_ID` | no | — | Webhook id used by the verifier (planned) |
| `PAYPAL_TIMEOUT_SECONDS` | no | `15` | Per-request timeout |
| `PAYPAL_MAX_RETRIES` | no | `2` | Extra attempts for retryable failures |
| `LLM_MODE` | yes | — | `mock` or `live` (LLM not implemented yet) |
| `DEMO_MODE` | yes | — | Enables demo-only affordances (planned) |
| `JOBS_MODE` | yes | — | `inline` today; Workflows later |

## Frontend variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | yes | Base URL of the FastAPI app |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | in Clerk mode | Clerk browser key |
| `CLERK_SECRET_KEY` | in Clerk mode | Clerk server key for the Next.js middleware |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | no | Custom sign-in route |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | no | Custom sign-up route |

`NEXT_PUBLIC_*` variables are embedded in the browser bundle. Never put a
secret behind that prefix.

## Fail-closed rules

`backend/app/core/config.py` validates the combination at startup and refuses
to boot when a rule is broken. This is intentional: a misconfigured money app
should not start in an ambiguous state.

| Rule | Why |
|------|-----|
| `AUTH_MODE=dev` + `APP_ENV=production` → refuse | No password-free production |
| `AUTH_MODE=dev` without `DEV_USER_EMAIL` → refuse | The demo user must be explicit |
| `AUTH_MODE=clerk` without secret or authorized parties → refuse | Never half-configure auth |
| `PAYPAL_MODE=mock` + `APP_ENV=production` → refuse | The hosted demo must use sandbox |
| `PAYPAL_MODE=live` outside production → refuse | Prevent accidental real money |
| `PAYPAL_MODE` ≠ `mock` without credentials → refuse | No silent unauthenticated calls |
| `PAYPAL_TIMEOUT_SECONDS <= 0` → refuse | Avoid instant timeouts |
| `PAYPAL_MAX_RETRIES < 0` → refuse | Avoid meaningless retry config |

## Local `.env` example

```env
APP_ENV=development
SECRET_KEY=change-me-to-a-long-random-string
DATABASE_URL=postgresql+asyncpg://vizlify:vizlify@localhost:5432/vizlify
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000

AUTH_MODE=dev
DEV_USER_EMAIL=demo@vizlify.space

PAYPAL_MODE=mock
LLM_MODE=mock
DEMO_MODE=true
JOBS_MODE=inline
```

## Docker Compose overrides

Compose always sets `APP_ENV=development`, points `DATABASE_URL` at the `db`
service and sets `CORS_ORIGINS`/`FRONTEND_URL` to `localhost:3000`. Everything
else comes from `backend/.env` (optional) or the image defaults.

## Secrets

- `.env` files are gitignored. Do not commit real keys.
- `frontend/.env.local` is for local-only values.
- Clerk publishable keys are public by design; Clerk secret keys are not.
- PayPal client secrets and webhook ids never reach the browser.
- The hosted demo should use a platform secret store (Render env group), not a
  committed file.

Next: [Project structure](./project-structure.md) →
