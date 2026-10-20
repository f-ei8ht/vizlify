# Vizlify — what is left

**Last updated:** Wed Oct 21, 2026
**Deadline:** Fri Nov 13, 2026, 1:30 am IST (Nov 12, 12:00 pm PT)
**Current mode:** the full money loop runs with `PAYPAL_MODE=mock`. No keys needed.

This file is the work tracker. The narrative version is
[`docs/09-project/status-and-roadmap.md`](docs/09-project/status-and-roadmap.md).
AG Studio is deliberately parked.

---

## 1. What I need from you

Everything below is optional for local development and required for real sandbox
verification. Put the values in `backend/.env` (gitignored) and restart the API.

### PayPal sandbox (needed to verify real invoices/payouts)

| Item | Env variable | Where to get it |
|------|--------------|-----------------|
| App client id | `PAYPAL_CLIENT_ID` | developer.paypal.com → Apps & Credentials → Sandbox → your app |
| App secret | `PAYPAL_CLIENT_SECRET` | Same app page |
| Webhook id | `PAYPAL_WEBHOOK_ID` | Same app → Webhooks → add `https://<public-url>/webhooks/paypal` |
| Agency business account | — | Testing Tools → Sandbox Accounts → Business |
| Client + freelancer accounts | — | Testing Tools → Sandbox Accounts → Personal (3) |

Checklist for the PayPal app:

- [ ] Invoicing enabled on the sandbox app
- [ ] Payouts enabled and the business balance funded
- [ ] Webhook subscribed to `INVOICING.INVOICE.*` and `PAYMENT.PAYOUTS*`
- [ ] Webhook URL is public HTTPS (cloudflared tunnel locally)
- [ ] `PAYPAL_MODE=sandbox` in `backend/.env`
- [ ] Sandbox logins recorded in the judge guide / README

### Clerk (hosted demo only)

`backend/.env` already contains Clerk test values; confirm they belong to the
app you will demo.

| Item | Env variable |
|------|--------------|
| Publishable key | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (frontend) |
| Secret key | `CLERK_SECRET_KEY` (backend and frontend) |
| JWT public key | `CLERK_JWT_KEY` (backend) |
| Authorized parties | `CLERK_AUTHORIZED_PARTIES=http://localhost:3000,https://vizlify.space` |

### Cerebras (only when we start the AI)

| Item | Env variable |
|------|--------------|
| API key | `CEREBRAS_API_KEY` (not in config yet; added with the LLM slice) |
| Model id | `LLM_MODEL` |
| Mode | `LLM_MODE=live` (keep `mock` for local/CI) |

### AG Studio (parked)

- [ ] Start the 45-day trial when the dashboard work begins
- [ ] Ask the AG Grid team on PayPal Discord for an extension through Dec 15
- [ ] Key stays in the environment only: `NEXT_PUBLIC_AG_STUDIO_LICENSE`
- [ ] Never commit the key

---

## 2. Done

- [x] Monorepo, Docker Compose, Dockerfiles, health checks
- [x] PostgreSQL schema, Alembic migrations, demo seed
- [x] Clerk auth + fail-closed `dev` mode + user provisioning
- [x] Clients, projects, milestones, team CRUD with ownership
- [x] PayPal transport: OAuth cache, retries, idempotency, mock mode
- [x] Approval queue and executor (`GET /actions`, approve, reject)
- [x] Idempotent proposals (`dedupe_key`) and `409` on double approve
- [x] Immutable audit log writes for propose/approve/reject/execute
- [x] Spend caps per action and per day
- [x] Invoice create + send, list/detail, remind, cancel, refresh
- [x] Milestone `done` creates an invoice proposal
- [x] PayPal webhooks: signature verification, dedupe, invoice/payout handlers
- [x] Payout preparation with largest-remainder split
- [x] Payout batch execution and item/batch status webhooks
- [x] Frontend API types and query hooks for actions, invoices, payouts
- [x] One working screen: `/dashboard` with approvals, invoices and payouts
- [x] Key-free frontend mode (Clerk is optional when no publishable key is set)
- [x] Handbook (42 pages) + judge guide
- [x] 108 backend tests, 91% coverage

---

## 3. Next, in order

### A. Verify against the real PayPal sandbox

- [ ] Add the sandbox keys and set `PAYPAL_MODE=sandbox`
- [ ] Tunnel the API and register the webhook
- [ ] Create + send one real sandbox invoice
- [ ] Pay it as the sandbox personal account
- [ ] Confirm `INVOICING.INVOICE.PAID` flips the invoice and queues the payout
- [ ] Approve the payout and confirm the batch in the sandbox dashboard
- [ ] Record the results in the judge guide

### B. One screen (no AG Studio yet)

- [x] `/dashboard` page: approval queue, invoices, payouts
- [x] Approve/reject buttons wired to the query hooks
- [x] Invoice status badges and a refresh button
- [x] Sandbox banner on every page
- [x] Loading, empty and error states via `DataState`
- [ ] Polish: invoices link to their milestone, activity feed, mobile pass

### C. AI scope from a brief (Cerebras)

- [ ] `app/ai/client.py` (OpenAI-compatible), `LLM_MODEL`, key validation
- [ ] `LLM_MODE=mock` deterministic scope output
- [ ] Structured scope schema + retry on invalid output
- [ ] Eval harness with 10 briefs in CI
- [ ] `POST /briefs`, status polling, editable draft
- [ ] "Create proposals" from an approved draft

### D. Collections (nudge-bot)

- [ ] Overdue detection (daily sweep)
- [ ] Tone-aware reminder copy from `client.tone_preference`
- [ ] Reminder proposals for all overdue invoices
- [ ] "Who Owes Me" data endpoint

### E. AG Studio Money Board (later)

- [ ] Trial license and spike (App Router, data, agent adapter)
- [ ] Three P0 widgets: Who Owes Me, Cash runway, Approval queue
- [ ] Brand theme + sandbox ribbon
- [ ] Studio Agent Framework adapter through the FastAPI LLM proxy
- [ ] NL-to-widget demo

### F. Deploy and harden

- [ ] `render.yaml` (web, api, Postgres, cron)
- [ ] `https://vizlify.space` + `https://api.vizlify.space`
- [ ] Clerk production keys, webhook URL, seed
- [ ] CI (GitHub Actions or Render build command)
- [ ] Rate limits, security headers, Sentry
- [ ] Playwright critical path

---

## 4. Verify what exists today

```bash
# Backend
cd backend
uv run ruff check .
uv run pytest

# Frontend
cd frontend
bun run lint
bun run typecheck

# Full stack
cd ..
docker compose up --build -d
docker compose exec api python -m app.scripts.seed
```

Manual money loop (mock PayPal):

```bash
# 1. Pick a milestone
curl -s localhost:8000/projects
curl -s localhost:8000/projects/<project-id>/milestones

# 2. Mark it done -> invoice proposal
curl -s -X PATCH localhost:8000/milestones/<milestone-id> \
  -H 'Content-Type: application/json' -d '{"status":"done"}'

# 3. Approve it -> PayPal invoice sent
curl -s -X POST localhost:8000/actions/<action-id>/approve

# 4. Inspect
curl -s localhost:8000/invoices

# 5. Simulate the paid webhook
curl -s -X POST localhost:8000/webhooks/paypal \
  -H 'Content-Type: application/json' \
  -d '{"id":"WH-1","event_type":"INVOICING.INVOICE.PAID",
       "resource":{"id":"<paypal-invoice-id>","status":"PAID"}}'

# 6. Approve the payout proposal, then execute the payout proposal
curl -s 'localhost:8000/actions?status=pending'
curl -s -X POST localhost:8000/actions/<payout-action-id>/approve
curl -s -X POST localhost:8000/payouts/<payout-id>/execute
curl -s -X POST localhost:8000/actions/<execute-action-id>/approve
```

Reset the demo at any time:

```bash
docker compose down -v
docker compose up -d
docker compose exec api python -m app.scripts.seed
```

---

## 5. Known limitations

| Limitation | Impact | Plan |
|------------|--------|------|
| Only one screen | No client/project detail pages yet | After sandbox verification |
| `PAYPAL_MODE=mock` skips signature checks | Local only; sandbox verifies | Never run mock in production (config refuses) |
| Failed actions cannot be retried | A failed proposal stays failed | Add a retry endpoint later |
| No HTTP-level idempotency | Duplicate approve is `409`, but duplicate create proposals rely on `dedupe_key` | Fine for the demo |
| No rate limiting or security headers | Hardening gap | Before public hosting |
| AG Studio not installed | Sponsor dashboard missing | Parked by request |
| CI not configured | Tests run locally / in Render build | After the demo path |
| Git commit signing blocked | Changes are staged, not committed | Unlock the SSH key or commit unsigned |

---

## 6. Environment quick reference

`backend/.env` for the mock demo:

```env
APP_ENV=development
AUTH_MODE=dev
DEV_USER_EMAIL=demo@vizlify.space
PAYPAL_MODE=mock
PAYPAL_WEBHOOK_ID=
PAYOUT_MAX_PER_ACTION=10000.00
PAYOUT_MAX_PER_DAY=50000.00
LLM_MODE=mock
DEMO_MODE=true
JOBS_MODE=inline
```

For sandbox verification, change only:

```env
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_WEBHOOK_ID=...
```

Restart after changing env:

```bash
docker compose up -d --build api
```
