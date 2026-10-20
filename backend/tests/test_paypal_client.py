from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.config import Settings, settings
from app.core.errors import ErrorCode
from app.main import create_app
from app.paypal import build_client, build_mock_transport
from app.paypal.client import (
    MAX_REQUEST_ID_LENGTH,
    PayPalClient,
    PayPalConfig,
    new_request_id,
)
from app.paypal.deps import get_paypal
from app.paypal.errors import (
    PayPalAuthError,
    PayPalRateLimited,
    PayPalRejectedError,
    PayPalUnavailable,
)

TOKEN_PATH = "/v1/oauth2/token"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SleepRecorder:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


class SlowTransport(httpx.AsyncBaseTransport):
    """Lets concurrent requests overlap so the token lock is exercised."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.01)
        self.requests.append(request)
        return self._handler(request)


@pytest.fixture
async def paypal() -> AsyncIterator[Callable[..., PayPalClient]]:
    clients: list[PayPalClient] = []

    def factory(
        handler: Callable[[httpx.Request], httpx.Response],
        *,
        clock: FakeClock | None = None,
        sleeper: SleepRecorder | None = None,
        max_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> PayPalClient:
        config = PayPalConfig(
            base_url="https://api-m.sandbox.paypal.com",
            client_id="client-id",
            client_secret="super-secret",
            timeout_seconds=1.0,
            max_retries=max_retries,
        )
        client = PayPalClient(
            config,
            transport=transport or httpx.MockTransport(handler),
            clock=clock or FakeClock(),
            sleep=sleeper or SleepRecorder(),
        )
        clients.append(client)
        return client

    yield factory
    for client in clients:
        await client.aclose()


def token_response(token: str = "token-1") -> httpx.Response:
    return httpx.Response(200, json={"access_token": token, "expires_in": 32400})


def requests_to(requests: list[httpx.Request], path: str) -> list[httpx.Request]:
    return [request for request in requests if request.url.path == path]


async def test_token_is_fetched_once_and_reused(paypal) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == TOKEN_PATH:
            return token_response()
        return httpx.Response(200, json={"ok": True})

    client = paypal(handler)

    await client.get("/v2/invoicing/invoices/1")
    await client.get("/v2/invoicing/invoices/2")

    assert len(requests_to(seen, TOKEN_PATH)) == 1
    api_requests = [request for request in seen if request.url.path != TOKEN_PATH]
    assert [request.headers["Authorization"] for request in api_requests] == ["Bearer token-1"] * 2


async def test_token_is_refreshed_before_it_expires(paypal) -> None:
    clock = FakeClock()
    tokens = iter(["token-1", "token-2"])
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == TOKEN_PATH:
            return token_response(next(tokens))
        return httpx.Response(200, json={"ok": True})

    client = paypal(handler, clock=clock)

    await client.get("/x")
    clock.advance(32400)
    await client.get("/x")

    assert len(requests_to(seen, TOKEN_PATH)) == 2
    assert requests_to(seen, "/x")[-1].headers["Authorization"] == "Bearer token-2"


async def test_concurrent_requests_share_one_token_fetch(paypal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return token_response()
        return httpx.Response(200, json={"ok": True})

    transport = SlowTransport(handler)
    client = paypal(handler, transport=transport)

    await asyncio.gather(*(client.get("/x") for _ in range(5)))

    assert len(requests_to(transport.requests, TOKEN_PATH)) == 1
    assert len(requests_to(transport.requests, "/x")) == 5


async def test_401_refreshes_the_token_and_retries_once(paypal) -> None:
    token_calls = 0
    api_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls, api_calls
        if request.url.path == TOKEN_PATH:
            token_calls += 1
            return token_response(f"token-{token_calls}")
        api_calls += 1
        if api_calls == 1:
            return httpx.Response(
                401, json={"name": "AUTHENTICATION_FAILURE", "debug_id": "debug-401"}
            )
        return httpx.Response(200, json={"id": "INV2-1"})

    client = paypal(handler)

    response = await client.get("/v2/invoicing/invoices/INV2-1")

    assert response.payload == {"id": "INV2-1"}
    assert (token_calls, api_calls) == (2, 2)


async def test_second_401_raises_an_auth_error(paypal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return token_response()
        return httpx.Response(401, json={"name": "AUTHENTICATION_FAILURE"})

    client = paypal(handler)

    with pytest.raises(PayPalAuthError) as error:
        await client.get("/x")

    assert error.value.code == ErrorCode.INTEGRATION_ERROR
    assert error.value.status_code == 401


async def test_429_honours_retry_after(paypal) -> None:
    sleeper = SleepRecorder()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == TOKEN_PATH:
            return token_response()
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={})
        return httpx.Response(200, json={"ok": True})

    client = paypal(handler, sleeper=sleeper)

    response = await client.get("/x")

    assert response.status_code == 200
    assert sleeper.calls == [2.0]


async def test_5xx_backs_off_and_then_raises(paypal) -> None:
    sleeper = SleepRecorder()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == TOKEN_PATH:
            return token_response()
        attempts += 1
        return httpx.Response(503, json={"name": "SYSTEM_ERROR", "debug_id": "debug-503"})

    client = paypal(handler, sleeper=sleeper, max_retries=2)

    with pytest.raises(PayPalUnavailable) as error:
        await client.get("/x")

    assert attempts == 3
    assert len(sleeper.calls) == 2
    assert sleeper.calls[1] >= sleeper.calls[0]
    assert error.value.debug_id == "debug-503"
    assert error.value.status_code == 503


async def test_5xx_is_not_retried_without_a_request_id(paypal) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == TOKEN_PATH:
            return token_response()
        attempts += 1
        return httpx.Response(500, json={})

    client = paypal(handler)

    with pytest.raises(PayPalUnavailable):
        await client.post("/v1/payments/payouts", json={})

    assert attempts == 1


async def test_retryable_write_reuses_the_same_request_id(paypal) -> None:
    request_ids: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return token_response()
        request_ids.append(request.headers.get("PayPal-Request-Id"))
        if len(request_ids) < 3:
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"ok": True})

    client = paypal(handler)

    await client.post("/v1/payments/payouts", json={}, request_id="payout-abc")

    assert request_ids == ["payout-abc"] * 3


async def test_4xx_is_not_retried_and_surfaces_the_debug_id(paypal) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == TOKEN_PATH:
            return token_response()
        attempts += 1
        return httpx.Response(
            422,
            json={
                "name": "UNPROCESSABLE_ENTITY",
                "message": "The invoice is already sent.",
                "debug_id": "debug-422",
            },
        )

    client = paypal(handler)

    with pytest.raises(PayPalRejectedError) as error:
        await client.get("/x")

    assert attempts == 1
    assert error.value.status_code == 422
    assert error.value.error_name == "UNPROCESSABLE_ENTITY"
    assert error.value.debug_id == "debug-422"
    assert error.value.details == [
        {"field": "paypal_error", "message": "UNPROCESSABLE_ENTITY"},
        {"field": "debug_id", "message": "debug-422"},
    ]
    assert "super-secret" not in str(error.value)


async def test_timeout_is_retried_and_then_maps_to_unavailable(paypal) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == TOKEN_PATH:
            return token_response()
        attempts += 1
        raise httpx.ReadTimeout("slow PayPal")

    client = paypal(handler, max_retries=1)

    with pytest.raises(PayPalUnavailable):
        await client.get("/x")

    assert attempts == 2


async def test_rate_limit_that_exhausts_retries_is_reported(paypal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return token_response()
        return httpx.Response(429, json={"name": "RATE_LIMIT_EXCEEDED"})

    client = paypal(handler, max_retries=0)

    with pytest.raises(PayPalRateLimited) as error:
        await client.get("/x")

    assert error.value.status_code == 429


async def test_empty_response_body_is_allowed(paypal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return token_response()
        return httpx.Response(204)

    client = paypal(handler)

    response = await client.post("/v2/invoicing/invoices/INV2-1/send")

    assert response.status_code == 204
    assert response.payload is None


def test_request_ids_are_deterministic_and_bounded() -> None:
    first = new_request_id("payout", "invoice-id", 42)
    second = new_request_id("payout", "invoice-id", 42)

    assert first == second
    assert first.startswith("payout-")
    assert len(first) <= MAX_REQUEST_ID_LENGTH
    assert len(new_request_id("a" * 100, "x")) <= MAX_REQUEST_ID_LENGTH
    assert new_request_id("invoice", "x") != first


async def test_oversized_request_id_is_rejected(paypal) -> None:
    client = paypal(lambda request: token_response())

    with pytest.raises(ValueError):
        await client.post("/x", request_id="a" * (MAX_REQUEST_ID_LENGTH + 1))


async def test_mock_transport_supports_the_invoice_flow() -> None:
    client = PayPalClient(PayPalConfig.mock(), transport=build_mock_transport())
    try:
        number = await client.post("/v2/invoicing/generate-next-invoice-number")
        created = await client.post(
            "/v2/invoicing/invoices",
            json={"detail": {"invoice_number": "VIZ-0001", "currency_code": "USD"}},
            request_id="invoice-1",
        )
        duplicate = await client.post(
            "/v2/invoicing/invoices",
            json={"detail": {"invoice_number": "VIZ-0001", "currency_code": "USD"}},
            request_id="invoice-1",
        )
    finally:
        await client.aclose()

    assert number.payload == {"invoice_number": "VIZ-0001"}
    assert created.status_code == 201
    assert created.header("Location", "").endswith(created.payload["id"])
    assert duplicate.payload["id"] == created.payload["id"]


async def test_build_client_selects_the_mock_transport(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PAYPAL_MODE", "mock")
    client = build_client(settings)

    try:
        response = await client.post("/v2/invoicing/generate-next-invoice-number")
    finally:
        await client.aclose()

    assert response.payload == {"invoice_number": "VIZ-0001"}


async def test_bad_credentials_raise_an_auth_error(paypal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"name": "AUTHENTICATION_FAILURE"})

    client = paypal(handler)

    with pytest.raises(PayPalAuthError, match="credentials"):
        await client.get("/x")


async def test_missing_access_token_is_reported(paypal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"token_type": "Bearer"})

    client = paypal(handler)

    with pytest.raises(PayPalUnavailable, match="no access token"):
        await client.get("/x")


async def test_non_json_body_yields_no_payload(paypal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            return token_response()
        return httpx.Response(200, text="not json")

    client = paypal(handler)

    assert (await client.get("/x")).payload is None


async def test_invalid_retry_after_falls_back_to_backoff(paypal) -> None:
    sleeper = SleepRecorder()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == TOKEN_PATH:
            return token_response()
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "later"}, json={})
        return httpx.Response(200, json={"ok": True})

    client = paypal(handler, sleeper=sleeper)

    assert (await client.get("/x")).status_code == 200
    assert len(sleeper.calls) == 1
    assert sleeper.calls[0] >= 0.25


async def test_connection_errors_are_retried_then_reported(paypal) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == TOKEN_PATH:
            return token_response()
        attempts += 1
        raise httpx.ConnectError("connection refused")

    client = paypal(handler, max_retries=1)

    with pytest.raises(PayPalUnavailable, match="reach PayPal"):
        await client.get("/x")

    assert attempts == 2


async def test_request_ids_must_be_usable(paypal) -> None:
    client = paypal(lambda request: token_response())

    with pytest.raises(ValueError, match="empty"):
        await client.post("/x", request_id="")
    with pytest.raises(ValueError, match="ASCII"):
        await client.post("/x", request_id="héllo")
    with pytest.raises(ValueError, match="start with"):
        await client.get("v2/invoicing/invoices")


async def test_mock_transport_covers_payouts_and_webhooks() -> None:
    client = PayPalClient(PayPalConfig.mock(), transport=build_mock_transport())
    try:
        payout = await client.post(
            "/v1/payments/payouts",
            json={"sender_batch_header": {"sender_batch_id": "batch-1"}, "items": []},
            request_id="payout-1",
        )
        verification = await client.post(
            "/v1/notifications/verify-webhook-signature", json={"webhook_id": "wh-1"}
        )
        with pytest.raises(PayPalRejectedError) as error:
            await client.get("/not-a-real-endpoint")
    finally:
        await client.aclose()

    assert payout.status_code == 201
    assert payout.payload["batch_header"]["payout_batch_id"].startswith("MOCK-BATCH-")
    assert verification.payload == {"verification_status": "SUCCESS"}
    assert error.value.error_name == "MOCK_ROUTE_NOT_IMPLEMENTED"


def test_config_from_settings_uses_the_derived_base_url() -> None:
    configured = build_settings(
        PAYPAL_MODE="sandbox",
        PAYPAL_CLIENT_ID="client-id",
        PAYPAL_CLIENT_SECRET="secret",
        PAYPAL_TIMEOUT_SECONDS=5,
        PAYPAL_MAX_RETRIES=1,
    )

    config = PayPalConfig.from_settings(configured)

    assert config.base_url == "https://api-m.sandbox.paypal.com"
    assert (config.client_id, config.client_secret) == ("client-id", "secret")
    assert (config.timeout_seconds, config.max_retries) == (5.0, 1)


def test_get_paypal_builds_once_and_caches_on_the_app(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PAYPAL_MODE", "mock")
    app = SimpleNamespace(state=SimpleNamespace())
    request = Request({"type": "http", "app": app, "method": "GET", "path": "/", "headers": []})

    first = get_paypal(request)
    second = get_paypal(request)

    assert first is second
    assert request.app.state.paypal is first


async def test_lifespan_builds_the_client() -> None:
    app = create_app()

    async with app.router.lifespan_context(app):
        assert isinstance(app.state.paypal, PayPalClient)


def build_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "APP_ENV": "development",
        "SECRET_KEY": "x" * 32,
        "DATABASE_URL": "sqlite+aiosqlite://",
        "CORS_ORIGINS": "http://localhost:3000",
        "FRONTEND_URL": "http://localhost:3000",
        "AUTH_MODE": "dev",
        "DEV_USER_EMAIL": "demo@example.com",
        "LLM_MODE": "mock",
        "DEMO_MODE": True,
        "JOBS_MODE": "inline",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_paypal_mode_defaults_to_mock() -> None:
    assert build_settings().PAYPAL_MODE == "mock"


def test_mock_mode_is_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="PAYPAL_MODE=mock"):
        build_settings(
            APP_ENV="production",
            AUTH_MODE="clerk",
            CLERK_SECRET_KEY="sk_test",
            CLERK_AUTHORIZED_PARTIES="https://vizlify.space",
            PAYPAL_MODE="mock",
        )


def test_sandbox_mode_requires_credentials() -> None:
    with pytest.raises(ValidationError, match="PAYPAL_CLIENT_ID"):
        build_settings(PAYPAL_MODE="sandbox")


def test_base_url_follows_the_mode() -> None:
    sandbox = build_settings(
        PAYPAL_MODE="sandbox", PAYPAL_CLIENT_ID="id", PAYPAL_CLIENT_SECRET="secret"
    )
    live = build_settings(
        APP_ENV="production",
        AUTH_MODE="clerk",
        CLERK_SECRET_KEY="sk_test",
        CLERK_AUTHORIZED_PARTIES="https://vizlify.space",
        PAYPAL_MODE="live",
        PAYPAL_CLIENT_ID="id",
        PAYPAL_CLIENT_SECRET="secret",
    )

    assert sandbox.paypal_base_url == "https://api-m.sandbox.paypal.com"
    assert live.paypal_base_url == "https://api-m.paypal.com"


def test_live_mode_is_refused_outside_production() -> None:
    with pytest.raises(ValidationError, match="PAYPAL_MODE=live"):
        build_settings(
            APP_ENV="development",
            PAYPAL_MODE="live",
            PAYPAL_CLIENT_ID="id",
            PAYPAL_CLIENT_SECRET="secret",
        )


def test_timeouts_and_retries_are_validated() -> None:
    with pytest.raises(ValidationError, match="PAYPAL_TIMEOUT_SECONDS"):
        build_settings(PAYPAL_TIMEOUT_SECONDS=0)
    with pytest.raises(ValidationError, match="PAYPAL_MAX_RETRIES"):
        build_settings(PAYPAL_MAX_RETRIES=-1)
