# Vizlify

**An AI agent that does an agency's money work: it proposes, you approve, PayPal executes.**

Freelance agencies lose hours every month writing invoices, chasing late payers, and splitting money by hand. Vizlify drafts the scope from a client brief, bills each milestone through PayPal, chases overdue invoices in the right tone, and prepares team payouts. **The AI can only propose. Nothing moves until a human approves.**

Built for the **PayPal AI Hackathon**. Open source under the [MIT License](./LICENSE).

![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.14-blue) ![next](https://img.shields.io/badge/next.js-16-black) ![bun](https://img.shields.io/badge/bun-1.x-fbf0df?logo=bun&logoColor=black) ![fastapi](https://img.shields.io/badge/fastapi-0.143+-teal) ![clerk](https://img.shields.io/badge/auth-clerk-6C47FF)

- **Live demo:** `https://vizlify.space` *(replace)*
- **Demo video (under 3 min):** `https://youtube.com/...` *(replace)*
- **Run it locally:** see [Quick start](#quick-start-about-5-minutes-no-api-keys-needed)

> **Sandbox only.** This version uses the PayPal sandbox. No real money moves.

## What it does

1. **Brief to scope:** paste a client brief, and the AI drafts milestones and prices.
2. **Milestone billing:** approved milestones become PayPal invoices.
3. **Late-payment nudge-bot:** overdue invoices get friendly, tone-aware reminders.
4. **Automatic team payouts:** when a client pays, the split is prepared and sent through the PayPal Payouts API after approval.
5. **Dispute assistant:** summarises disputes and drafts responses.
6. **Chat with your finances:** "Who owes me money?", "Show revenue by client this month" (builds a live dashboard widget).

## How PayPal and AI are used

| PayPal | AI |
|--------|----|
| Invoicing, Payouts, Orders, Webhooks (signature-verified), Disputes, Transaction Search for reconciliation | Cerebras (OpenAI-compatible API) with structured outputs and tool calling; an approval-gated agent; AG Studio Agent Framework for natural-language dashboards |

Every action that moves money or contacts a client becomes a proposal in an approval queue; nothing executes until a human confirms it.

## Sponsor tools

| Tool | How it is used |
|------|----------------|
| **AG Studio (AG Grid)** | The Money Board dashboard: custom widgets, theme, and the Studio Agent Framework |
| **APIMatic** | PayPal Context Plugin used as the integration reference; see the [APIMatic note](./docs/04-backend/paypal-client.md#apimatic-evidence) |
| **Render** | Hosting, Postgres, Cron Job, and Render Workflows for parallel AI tasks; see [Deployment](./docs/06-operations/deployment.md) |

## Authentication

Accounts are handled by **Clerk** (sign-in UI + session tokens). The Next.js app signs the user in and attaches a short-lived session token as a `Bearer` header on every API call; the FastAPI backend verifies it locally against Clerk's public key (`clerk-backend-api`, no per-request call to Clerk) and maps the Clerk user to the local `users` row, matching by email and creating the row on first sign-in.

For local runs and for judges, the whole app still works with **no Clerk keys**. `AUTH_MODE` picks the strategy:

| Mode | Used for | Clerk keys | Sign-in |
|------|----------|-----------|---------|
| `dev` | local development, judges | not needed | the seeded demo account |
| `clerk` | hosted demo, production | `CLERK_*` | Clerk's hosted sign-in |

`dev` is the default and only ever allowed when `APP_ENV != production`; it is refused (fail-closed) in production.

Backend env for Clerk mode:

```env
AUTH_MODE=clerk
CLERK_SECRET_KEY=sk_test_...
CLERK_JWT_KEY=-----BEGIN PUBLIC KEY-----...-----END PUBLIC KEY-----
CLERK_AUTHORIZED_PARTIES=http://localhost:3000,https://vizlify.space
```

For `AUTH_MODE=dev` set `DEV_USER_EMAIL` to the demo account email. All of these values come from the environment; nothing is defaulted in code.

Frontend env: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, and the sign-in/up URLs.

## PayPal

`PAYPAL_MODE` picks the transport: `mock` (default, in-process fake, no keys), `sandbox`, or `live` (refused outside production). The client caches OAuth tokens, refreshes them before expiry, retries `429`/`5xx` with backoff, and sends a deterministic `PayPal-Request-Id` on every write so retries cannot duplicate an invoice or payout.

```env
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_WEBHOOK_ID=...
```

See [the PayPal chapter](./docs/04-backend/paypal-client.md) for the sandbox setup and the full behaviour.

## Documentation

The project handbook starts at [`docs/README.md`](./docs/README.md). It covers the product, architecture (with Mermaid diagrams), the domain API, the database, the PayPal client, the frontend data layer, operations, architecture decisions and a reference section.

Good entry points:

- [What is Vizlify?](./docs/01-overview/what-is-vizlify.md) — the problem and the safety promise.
- [Architecture](./docs/03-architecture/system-overview.md) — components and boundaries.
- [API endpoints](./docs/08-reference/api-endpoints.md) — implemented and planned routes.
- [Project status](./docs/09-project/status-and-roadmap.md) — what is done and what is next.

## Quick start (about 5 minutes, no API keys needed)

Requires Docker.

```bash
git clone https://github.com/<you>/vizlify.git && cd vizlify
cp backend/.env.example backend/.env       # AUTH_MODE=dev and LLM_MODE=mock both work without any key
docker compose up --build -d
docker compose exec api python -m app.scripts.seed   # creates the demo agency and demo login
```

Then open http://localhost:3000 and sign in with the demo account in the judge guide below. Locally the app runs in `AUTH_MODE=dev`, so no Clerk, PayPal or LLM keys are needed.

## Judge guide

The hosted demo runs on a free-tier host, so the **first request after idle can take up to a minute** to wake up.

| Item | Value |
|------|-------|
| Authentication | The hosted demo signs in through Clerk. A local run uses `AUTH_MODE=dev` and needs no Clerk keys |
| Demo login (local, `AUTH_MODE=dev`) | `demo@vizlify.space` (no password; set by `DEV_USER_EMAIL`) |
| Hosted Clerk demo account | `<clerk demo email>` / `<password>` *(replace)* |
| PayPal sandbox payer (to pay an invoice) | `<sandbox personal email>` / `<password>` *(replace)* |
| LLM | `LLM_MODE=mock` is deterministic and needs no key. Set `LLM_MODE=live` with a Cerebras key for the real agent |
| Walkthrough | 1) Paste the sample brief. 2) Approve the proposed invoice. 3) Pay it as the sandbox payer. 4) Approve the payout split. 5) Click "time travel" to see the nudge-bot. See the [judge guide](./docs/09-project/judge-guide.md) |

## Tech stack

Next.js 16 (App Router, TypeScript, Tailwind, bun), Clerk (authentication), AG Studio, FastAPI (Python 3.14), SQLAlchemy 2 and Alembic, PostgreSQL 16, Cerebras, PayPal REST APIs, Render (Workflows, Cron, Postgres), Docker, GitHub Actions.

## Project status

The backend money loop works end to end: approvals and the executor, invoice create/send/remind/cancel, PayPal webhook verification and dedupe, and team payouts with deterministic splits and spend caps. Auth is Clerk on the frontend and verified on the backend, with a gated `dev` mode so the app runs locally without keys. The PayPal transport covers OAuth token caching, retries, idempotency and a key-free mock mode. The Next.js app has a working Money Board at `/dashboard` (approvals, invoices, payouts) on top of typed money query hooks; more screens and AG Studio are next. AG Studio is integrated later behind a client-only feature flag and needs its own trial key. See [`TODO.md`](./TODO.md) for the remaining work and the keys the sandbox needs.

## Development

Requires Docker. The whole stack is one command: PostgreSQL 16, the FastAPI API, and the Next.js web app.

```bash
cp backend/.env.example backend/.env
docker compose up --build -d
docker compose exec api python -m app.scripts.seed
```

Backend work (inside `backend/`):

```bash
uv sync
uv run alembic upgrade head                        # apply migrations
uv run alembic revision --autogenerate -m "change" # create a migration
uv run uvicorn app.main:app --reload --port 8000   # http://localhost:8000/docs
uv run ruff check . && uv run pytest               # lint + tests
```

With the API running, its schema is at `http://localhost:8000/openapi.json`. PayPal webhooks cannot reach `localhost`, so expose the API with `cloudflared tunnel --url http://localhost:8000` (or `ngrok http 8000`) while testing them.

Frontend work (inside `frontend/`):

```bash
bun install
bun run dev            # http://localhost:3000
bun run lint && bun run typecheck
```

## Licensing

Vizlify's code is MIT licensed. **AG Studio is a commercial product** under its own license and is not covered by the MIT license; you need your own AG Studio key to run the full dashboard. See [License and notices](./docs/09-project/license-and-notices.md).

## Contributing and security

Contributions are welcome: see [Contributing](./docs/09-project/contributing.md). Report vulnerabilities privately through GitHub's security advisories; see [Security](./docs/06-operations/security.md).

## Disclaimer

Vizlify is an independent hackathon project. It is not affiliated with or endorsed by PayPal. PayPal and other product names belong to their owners.

## Built during the hackathon

Vizlify was created from scratch during the PayPal AI Hackathon submission period (starting October 2026). The commit history shows the work.
