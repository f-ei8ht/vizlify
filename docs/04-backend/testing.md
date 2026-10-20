# Testing

> [Handbook index](../README.md) · [Part 4](./README.md) · **Status: Implemented (backend), Planned (frontend and e2e)**

The backend uses pytest with async tests, an in-memory database per test and
dependency overrides for the API client. No test touches the network.

## Commands

```bash
cd backend
uv run pytest              # full suite with coverage
uv run pytest --no-cov -q  # fast loop
uv run pytest tests/test_paypal_client.py -q
uv run ruff check .
```

`pyproject.toml` sets `asyncio_mode = "auto"`, so `async def test_*` needs no
decorator.

## Fixtures

`tests/conftest.py` provides four fixtures:

| Fixture | What it gives you |
|---------|-------------------|
| `session_factory` | Async engine + session factory on `sqlite+aiosqlite:///:memory:` |
| `db_session` | One session for arranging data directly |
| `client` | `httpx.AsyncClient` bound to the FastAPI app via `ASGITransport` |
| `seeded_client` | `client` plus the demo agency |

```python
async def override_get_db() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db
```

Each test gets a fresh schema, so tests cannot leak state into one another.

An autouse fixture forces `AUTH_MODE=dev`, which means requests resolve the
seeded demo user without a token.

## What is covered

| Area | Tests | Notes |
|------|-------|-------|
| Health and envelope | 3 | `/`, `/health`, unknown route |
| Response helpers | 2 | Envelope construction |
| Auth | 9 | dev mode, missing user, Clerk claim mapping |
| Clients | 8 | CRUD, validation, ownership, cascade delete |
| Projects | 4 | CRUD, unknown client, ownership |
| Milestones | 5 | CRUD, validation, ownership |
| Team | 3 | CRUD, share ceiling, ownership |
| Models | 7 | Relationships, enum values, money types |
| Seed | 4 | Idempotency and fixture validation |
| PayPal client | 33 | Token cache, retries, idempotency, errors, mock |
| Approvals and executor | 8 | Propose, approve, reject, `409`, audit, failure, ownership |
| Invoicing | 6 | Create/send, detail, remind, cancel, refresh, duplicate |
| Payouts | 11 | Split rounding, prepare, execute, both spend caps, dedupe |
| Webhooks | 5 | Bad signature, dedupe, cancelled/batch/item statuses, malformed body |

Current total: **108 tests**, ~91% statement coverage. `client.py` is 97%;
the PayPal transport and the split algorithm are fully covered.

## Patterns

### Arrange through the API

Prefer the public API over direct model inserts, except when creating a second
owner for isolation tests:

```python
async def test_update_client(seeded_client: AsyncClient) -> None:
    created = await seeded_client.post("/clients", json={"name": "Initech", "email": "b@i.dev"})
    client_id = created.json()["data"]["id"]

    response = await seeded_client.patch(f"/clients/{client_id}", json={"tone_preference": "firm"})

    assert response.json()["data"]["tone_preference"] == "firm"
```

### Assert the envelope, not just the status

```python
body = response.json()
assert body["error"] is None
assert body["data"]["name"] == "Initech"
```

### Prove ownership

Create a second user, insert their row directly, then assert it never appears
and cannot be fetched by id. Every resource suite has one such test.

### Freeze time and sleep in PayPal tests

The PayPal client accepts `clock` and `sleep` callables:

```python
client = PayPalClient(
    config,
    transport=httpx.MockTransport(handler),
    clock=FakeClock(),
    sleep=SleepRecorder(),
)
```

This makes token expiry and backoff deterministic without `time.sleep`.

### Test retries by counting attempts

```python
attempts = 0

def handler(request):
    nonlocal attempts
    attempts += 1
    return httpx.Response(503, json={})

with pytest.raises(PayPalUnavailable):
    await client.get("/x")

assert attempts == 3  # initial try + 2 retries
```

## What is not tested yet

- **Frontend:** no unit tests, no Playwright. The query hooks and API client
  are good candidates for Vitest once screens exist.
- **Migrations:** no test applies Alembic to a real Postgres. Run
  `alembic upgrade head` against Compose before merging schema work.
- **Webhooks:** no signature fixtures until the verifier exists.
- **Load:** no k6 or latency budget yet.

## Adding a feature test

1. Start with the smallest failing request (`401`, `422`, then `200`).
2. Cover the happy path, one validation failure and one ownership failure.
3. Assert side effects through a follow-up GET.
4. Keep one behavior per test; the name should read as a sentence.
5. Update the counts in this page and in
   [Project status](../09-project/status-and-roadmap.md) when they change.

Next: [App shell](../05-frontend/app-shell.md) →
