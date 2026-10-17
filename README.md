# Vizlify

**An AI agent that does an agency's money work: it proposes, you approve, PayPal executes.**

Freelance agencies lose hours every month writing invoices, chasing late payers, and splitting money by hand. Vizlify drafts the scope from a client brief, bills each milestone through PayPal, chases overdue invoices in the right tone, and prepares team payouts. **The AI can only propose. Nothing moves until a human approves.**

Built for the **PayPal AI Hackathon**. Open source under the [MIT License](./LICENSE).

![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.14-blue) ![next](https://img.shields.io/badge/next.js-16-black) ![bun](https://img.shields.io/badge/bun-1.x-fbf0df?logo=bun&logoColor=black) ![fastapi](https://img.shields.io/badge/fastapi-0.115+-teal)

- **Live demo:** `https://vizlify.space` *(replace)*
- **Demo video (under 3 min):** `https://youtube.com/...` *(replace)*
- **Full plan, features and technical reference:** [ROADMAP.md](./ROADMAP.md)

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

Details: [ROADMAP.md, Part B](./ROADMAP.md#part-b--technical-reference).

## Sponsor tools

| Tool | How it is used |
|------|----------------|
| **AG Studio (AG Grid)** | The Money Board dashboard: custom widgets, theme, and the Studio Agent Framework |
| **APIMatic** | PayPal Context Plugin used to build the PayPal integration; see `docs/apimatic.md` |
| **Render** | Hosting, Postgres, Cron Job, and Render Workflows for parallel AI tasks; see `docs/render.md` |

## Quick start (about 5 minutes, no API keys needed)

Requires Docker.

```bash
git clone https://github.com/<you>/vizlify.git && cd vizlify
cp backend/.env.example backend/.env       # LLM_MODE=mock works without any key
docker compose up --build -d
docker compose exec api python -m app.scripts.seed   # creates the demo agency and demo login
```

Then open http://localhost:3000 and sign in with the demo account in the judge guide below.

## Judge guide

The hosted demo runs on a free-tier host, so the **first request after idle can take up to a minute** to wake up.

| Item | Value |
|------|-------|
| Demo login | `demo@vizlify.space` / `<password>` *(replace)* |
| PayPal sandbox payer (to pay an invoice) | `<sandbox personal email>` / `<password>` *(replace)* |
| LLM | `LLM_MODE=mock` is deterministic and needs no key. Set `LLM_MODE=live` with a Cerebras key for the real agent |
| Walkthrough | 1) Paste the sample brief. 2) Approve the proposed invoice. 3) Pay it as the sandbox payer. 4) Approve the payout split. 5) Click "time travel" to see the nudge-bot. See `docs/judge-guide.md` |

## Tech stack

Next.js 16 (App Router, TypeScript, Tailwind, bun), AG Studio, FastAPI (Python 3.14), SQLAlchemy 2 and Alembic, PostgreSQL 16, Cerebras, PayPal REST APIs, Render (Workflows, Cron, Postgres), Docker, GitHub Actions.

## Project status

The repo currently holds the Phase 0 scaffold: the monorepo layout, a FastAPI app shell that serves `/health`, a Next.js 16 app shell (shadcn/ui, Tailwind v4, dark mode), Docker Compose and CI. The build order and remaining work are tracked in [ROADMAP.md](./ROADMAP.md). AG Studio is integrated later behind a client-only feature flag and needs its own trial key; until then the dashboard renders without it.

## Development

See [ROADMAP.md, section B12](./ROADMAP.md#b12-local-development-setup) for local setup, environment variables, webhook testing, tests and deployment.

## Licensing

Vizlify's code is MIT licensed. **AG Studio is a commercial product** under its own license and is not covered by the MIT license; you need your own AG Studio key to run the full dashboard. See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).

## Contributing and security

Contributions are welcome: see [CONTRIBUTING.md](./CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md). Report vulnerabilities as described in [SECURITY.md](./SECURITY.md).

## Disclaimer

Vizlify is an independent hackathon project. It is not affiliated with or endorsed by PayPal. PayPal and other product names belong to their owners.

## Built during the hackathon

Vizlify was created from scratch during the PayPal AI Hackathon submission period (starting October 2026). The commit history shows the work.
