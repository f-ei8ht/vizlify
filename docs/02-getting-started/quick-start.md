# Quick start

> [Handbook index](../README.md) · [Part 2](./README.md) · **Status: Implemented**

About five minutes, no API keys, no PayPal account.

## 1. Clone and configure

```bash
git clone <your-fork-url> vizlify
cd vizlify
cp backend/.env.example backend/.env
```

The example file ships with safe defaults:

```env
AUTH_MODE=dev        # no Clerk keys needed
LLM_MODE=mock        # no Cerebras key needed
PAYPAL_MODE=mock     # no PayPal keys needed
```

## 2. Start the stack

```bash
docker compose up --build -d
```

The API applies Alembic migrations on start, so a fresh database volume works
without an extra command. This builds and starts three services:

| Service | URL | What it is |
|---------|-----|------------|
| `db` | `127.0.0.1:5432` | PostgreSQL 16 |
| `api` | http://localhost:8000 | FastAPI; docs at `/docs` |
| `web` | http://localhost:3000 | Next.js 16 |

Wait for health checks:

```bash
docker compose ps
curl http://localhost:8000/health
# {"data":{"status":"ok"},"error":null}
```

## 3. Seed the demo agency

```bash
docker compose exec api python -m app.scripts.seed
```

The script is idempotent and prints the login it created:

```
Seeded Northwind Studio.
  login: demo@vizlify.space (AUTH_MODE=dev)
```

It creates **Northwind Studio**, two clients (Acme Co, Globex Corporation), a
$12,500 website redesign with three milestones, and three freelancers splitting
40/35/25.

## 4. Open the app

Go to http://localhost:3000. In `AUTH_MODE=dev` the API resolves the seeded
user automatically, so there is no password and no sign-in step.

> The home page redirects to `/dashboard`, the Money Board: approval queue,
> invoices and payouts. Approve a proposal there to run it. More screens are
> tracked in [Project status](../09-project/status-and-roadmap.md).

## 5. Explore the API

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json
- Health: http://localhost:8000/health

Try a read with the dev user:

```bash
curl http://localhost:8000/clients
```

## Working outside Docker

**Backend**

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
bun install
bun run dev
```

The frontend needs `NEXT_PUBLIC_API_URL=http://localhost:8000` (see
`.env.example`). Copy it to `frontend/.env.local` for local development.

## Useful commands

```bash
# Logs
docker compose logs -f api
docker compose logs -f web

# Stop / reset
docker compose down            # stop, keep data
docker compose down -v         # stop and delete the database volume

# Backend quality gate
cd backend && uv run ruff check . && uv run pytest

# Frontend quality gate
cd frontend && bun run lint && bun run typecheck
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 The demo workspace is not ready yet.` | Seed has not run | `docker compose exec api python -m app.scripts.seed` |
| API exits at startup with `AUTH_MODE=dev is not allowed` | `APP_ENV=production` with dev auth | Use Clerk mode, or run with `APP_ENV=development` |
| `PAYPAL_MODE=mock is not allowed when APP_ENV=production` | Production without PayPal credentials | Set `PAYPAL_MODE=sandbox` and keys, or run in development |
| Web loads but API calls fail | Wrong `NEXT_PUBLIC_API_URL` or CORS | Check `frontend/.env.local` and `CORS_ORIGINS` |
| Ports already in use | Another Postgres/Next/FastAPI | Stop it, or change the published ports in `compose.yaml` |

Next: [Environment](./environment.md) →
