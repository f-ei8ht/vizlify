# Judge guide

> [Handbook index](../README.md) · [Part 9](./README.md) · **Status: Implemented (API), Scaffolded (UI)**

A short path through what works today, and an honest map of the intended demo.

## Run it locally (no keys)

```bash
git clone <repository-url> vizlify
cd vizlify
cp backend/.env.example backend/.env
docker compose up --build -d
docker compose exec api python -m app.scripts.seed
```

Open **http://localhost:3000** and the API docs at
**http://localhost:8000/docs**.

| Item | Value |
|------|-------|
| Local login | `demo@vizlify.space` (no password, `AUTH_MODE=dev`) |
| Seeded agency | Northwind Studio |
| Clients | Acme Co, Globex Corporation |
| Project | Acme website redesign, USD |
| Milestones | $2,500 · $4,000 · $6,000 |
| Team split | Rida 40% · Maya 35% · Sam 25% |
| PayPal | `PAYPAL_MODE=mock`: no network, no keys |
| LLM | `LLM_MODE=mock`: no key (agent not wired yet) |

## What you can verify today

| Check | How |
|-------|-----|
| Health and envelope | `curl http://localhost:8000/health` |
| Seeded data | `curl http://localhost:8000/clients` |
| Owner scoping | Create a second user in a test, confirm rows never cross |
| Validation | `POST /clients` with an invalid email → `422` envelope |
| Team share ceiling | Add members totalling over 100% → `409` |
| Money as strings | Milestone amounts serialize as `"2500.00"` |
| Approval gate | A proposal can be approved once; a second approve returns `409` |
| Invoice flow | `PATCH` a milestone to `done`, approve the proposal, then `GET /invoices` |
| Paid webhook | `POST /webhooks/paypal` with `INVOICING.INVOICE.PAID` queues a payout |
| Payout split | Approving the payout proposal creates 40/35/25 items that sum to the total |
| Spend caps | Set a low `PAYOUT_MAX_PER_ACTION` and watch the payout get blocked |
| PayPal transport | `cd backend && uv run pytest tests/test_paypal_client.py` |
| Full suite | `cd backend && uv run pytest` — 108 tests, 91% coverage |

Open **http://localhost:3000/dashboard** for the Money Board: approve or reject
proposals, send and sync invoices, and propose/execute payouts. The complete
mock loop is written out in [`TODO.md`](../../TODO.md).

## The intended three-minute demo

```mermaid
flowchart LR
    Brief["Paste Acme's brief"] --> Scope["Approve proposed<br/>scope + milestones"]
    Scope --> Invoice["Approve invoice<br/>proposal"]
    Invoice --> Pay["Pay in PayPal<br/>sandbox"]
    Pay --> Split["Approve payout<br/>proposal"]
    Split --> Sent["Three sandbox<br/>payouts sent"]
    Sent --> Nudge["Time travel:<br/>overdue reminder"]
```

Steps and their status:

| Step | Status | Notes |
|------|--------|-------|
| 1. Paste a brief | Planned | Needs the LLM client and brief UI |
| 2. Approve the scope | Planned | Needs proposals and the approval queue |
| 3. Approve the invoice | **Implemented** | API; UI missing |
| 4. Pay as the sandbox payer | **Implemented** | Needs sandbox keys for the real payer |
| 5. Webhook marks it paid | **Implemented** | Signature verification + dedupe |
| 6. Approve the payout split | **Implemented** | Split maths, batch, item statuses |
| 7. Time travel to an overdue reminder | Planned | Needs the demo controls |

When the hosted demo is live, the Clerk account and sandbox payer credentials
will be published here and in the root README. **Never use real accounts.**

## What to look for in the code

| Property | Where to look |
|----------|---------------|
| The agent cannot execute | `services/executor.py` is reachable only from an approved proposal |
| Retries cannot duplicate money | `new_request_id` and `PayPal-Request-Id` in `app/paypal/client.py` |
| PayPal failures are contained | `PayPalError` → `502 integration_error`, raw body never returned |
| Exact money | `Numeric(12, 2)` and `Decimal`; strings on the wire |
| Splits add up | Largest-remainder rounding in `services/payouts.py` |
| No key-free production | `core/config.py` validators |
| Owner isolation | Every service filters by `owner_id` and returns `404` |
| Test discipline | 106 tests, 91% coverage, no network in tests |

## Known limits

The money loop is exposed and tested against mock PayPal; the dashboard screens
and real sandbox verification are next. [Project status](./status-and-roadmap.md)
and [`TODO.md`](../../TODO.md) list the remaining work.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401` on `/clients` | Run the seed; check `DEV_USER_EMAIL` |
| API exits at startup | Check the fail-closed rules in [Environment](../02-getting-started/environment.md) |
| Empty database | The API migrates on start; run the seed command |
| Web app shows the starter page | Expected; screens are the next milestone |
