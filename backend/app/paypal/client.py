"""PayPal REST transport: OAuth token cache, retries and idempotency.

Deliberately thin. The PayPal server SDKs are synchronous and awkward to mock,
so this module owns the two things every PayPal call needs and nothing else:
a cached bearer token and a retry policy that respects PayPal's own rules.

Rules taken from https://developer.paypal.com/invoicing/errors:
- refresh the token and retry once on 401;
- back off with jitter on 429 and 5xx;
- never retry any other 4xx;
- keep `PayPal-Request-Id` identical across retries.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from app.paypal.errors import (
    PayPalAuthError,
    PayPalError,
    PayPalRateLimited,
    PayPalRejectedError,
    PayPalUnavailable,
)

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

MAX_REQUEST_ID_LENGTH = 38
TOKEN_REFRESH_SKEW_SECONDS = 60
MAX_BACKOFF_SECONDS = 4.0
MAX_RETRY_AFTER_SECONDS = 30.0
RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

Clock = Callable[[], float]
Sleeper = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class PayPalConfig:
    base_url: str
    client_id: str
    client_secret: str
    timeout_seconds: float = 15.0
    max_retries: int = 2

    @classmethod
    def from_settings(cls, settings: Settings) -> PayPalConfig:
        return cls(
            base_url=settings.paypal_base_url,
            client_id=settings.PAYPAL_CLIENT_ID or "",
            client_secret=settings.PAYPAL_CLIENT_SECRET or "",
            timeout_seconds=settings.PAYPAL_TIMEOUT_SECONDS,
            max_retries=settings.PAYPAL_MAX_RETRIES,
        )

    @classmethod
    def mock(cls) -> PayPalConfig:
        return cls(
            base_url="https://api-m.sandbox.paypal.com",
            client_id="mock-client-id",
            client_secret="mock-client-secret",
        )


@dataclass(frozen=True, slots=True)
class PayPalResponse:
    status_code: int
    headers: Mapping[str, str]
    payload: dict[str, Any] | None

    def header(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name, default)


def new_request_id(kind: str, *parts: object) -> str:
    """A deterministic idempotency key, capped at PayPal's 38-character limit.

    Deterministic by design: a retried workflow re-run sends the same key, so
    PayPal returns the original resource instead of creating a duplicate.
    """
    slug = "".join(character for character in kind.lower() if character.isalnum())[:7]
    digest = hashlib.sha256(":".join([kind, *(str(part) for part in parts)]).encode()).hexdigest()
    return f"{slug or 'request'}-{digest[:30]}"


class PayPalClient:
    def __init__(
        self,
        config: PayPalConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Clock = time.monotonic,
        sleep: Sleeper = asyncio.sleep,
    ) -> None:
        self._config = config
        self._clock = clock
        self._sleep = sleep
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
            transport=transport,
            headers={"Accept": "application/json"},
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> PayPalResponse:
        return await self.request("GET", path, params=params, idempotent=True)

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> PayPalResponse:
        return await self.request("POST", path, json=json, request_id=request_id)

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
        idempotent: bool = False,
    ) -> PayPalResponse:
        if not path.startswith("/"):
            raise ValueError("PayPal paths must start with '/'.")
        if request_id is not None:
            _validate_request_id(request_id)

        method = method.upper()
        retryable = idempotent or request_id is not None or method in {"GET", "HEAD"}
        token = await self._access_token()
        response = await self._send(
            method,
            path,
            token=token,
            json=json,
            params=params,
            request_id=request_id,
            retryable=retryable,
        )
        if response.status_code == 401:
            token = await self._access_token(force=True)
            response = await self._send(
                method,
                path,
                token=token,
                json=json,
                params=params,
                request_id=request_id,
                retryable=retryable,
            )
        return self._handle(response, method, path)

    async def _access_token(self, *, force: bool = False) -> str:
        async with self._token_lock:
            now = self._clock()
            fresh_enough = now < self._token_expires_at - TOKEN_REFRESH_SKEW_SECONDS
            if not force and self._token and fresh_enough:
                return self._token

            response = await self._send(
                "POST",
                "/v1/oauth2/token",
                token=None,
                request_id=None,
                retryable=True,
                auth=httpx.BasicAuth(self._config.client_id, self._config.client_secret),
                content=b"grant_type=client_credentials",
                extra_headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            payload = self._json(response) or {}
            token = payload.get("access_token")
            if response.status_code >= 400:
                if response.status_code == 401:
                    raise PayPalAuthError(
                        "PayPal rejected the API credentials.",
                        status_code=401,
                    )
                raise self._error_from(response)
            if not isinstance(token, str) or not token:
                raise PayPalUnavailable("PayPal returned no access token.")

            expires_in = _as_float(payload.get("expires_in"), default=0.0)
            self._token = token
            self._token_expires_at = now + max(expires_in, TOKEN_REFRESH_SKEW_SECONDS)
            return token

    async def _send(
        self,
        method: str,
        path: str,
        *,
        token: str | None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
        retryable: bool = False,
        extra_headers: dict[str, str] | None = None,
        auth: httpx.Auth | None = None,
        content: bytes | None = None,
    ) -> httpx.Response:
        attempts = self._config.max_retries + 1 if retryable else 1
        headers = self._headers(token=token, json=json, request_id=request_id, extra=extra_headers)

        for attempt in range(attempts):
            last_attempt = attempt + 1 == attempts
            try:
                response = await self._http.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers=headers,
                    auth=auth,
                    content=content,
                )
            except httpx.TimeoutException as exc:
                if last_attempt:
                    raise PayPalUnavailable("PayPal did not respond in time.") from exc
                await self._backoff(attempt, retry_after=None)
                continue
            except httpx.TransportError as exc:
                if last_attempt:
                    raise PayPalUnavailable("Could not reach PayPal.") from exc
                await self._backoff(attempt, retry_after=None)
                continue

            if response.status_code in RETRYABLE_STATUSES and not last_attempt:
                await self._backoff(attempt, retry_after=_retry_after(response))
                continue
            return response

        raise PayPalUnavailable("PayPal is temporarily unavailable.")

    def _handle(self, response: httpx.Response, method: str, path: str) -> PayPalResponse:
        payload = self._json(response)
        if response.status_code < 400:
            return PayPalResponse(response.status_code, response.headers, payload)

        error = self._error_from(response)
        logger.warning(
            "PayPal %s %s failed: status=%s error=%s debug_id=%s",
            method,
            path,
            response.status_code,
            error.error_name,
            error.debug_id,
        )
        raise error

    def _error_from(self, response: httpx.Response) -> PayPalError:
        payload = self._json(response) or {}
        error_name = payload.get("name") if isinstance(payload.get("name"), str) else None
        debug_id = payload.get("debug_id") if isinstance(payload.get("debug_id"), str) else None
        status = response.status_code

        if status in {401, 403}:
            message = (
                "PayPal rejected the API credentials."
                if status == 401
                else "PayPal denied this request. Check the app's enabled features."
            )
            return PayPalAuthError(
                message, status_code=status, error_name=error_name, debug_id=debug_id
            )
        if status == 429:
            return PayPalRateLimited(
                "PayPal is rate limiting requests. Try again shortly.",
                status_code=status,
                error_name=error_name,
                debug_id=debug_id,
            )
        if status >= 500:
            return PayPalUnavailable(
                "PayPal is temporarily unavailable. Try again shortly.",
                status_code=status,
                error_name=error_name,
                debug_id=debug_id,
            )
        return PayPalRejectedError(
            "PayPal rejected the request.",
            status_code=status,
            error_name=error_name,
            debug_id=debug_id,
        )

    async def _backoff(self, attempt: int, *, retry_after: float | None) -> None:
        if retry_after is not None:
            delay = min(retry_after, MAX_RETRY_AFTER_SECONDS)
        else:
            delay = min(0.25 * (2**attempt), MAX_BACKOFF_SECONDS) + random.uniform(0, 0.25)
        await self._sleep(delay)

    @staticmethod
    def _headers(
        *,
        token: str | None,
        json: dict[str, Any] | None,
        request_id: str | None,
        extra: dict[str, str] | None,
    ) -> dict[str, str]:
        headers = dict(extra or {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if json is not None:
            headers["Content-Type"] = "application/json"
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        return headers

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any] | None:
        if not response.content:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None


def _validate_request_id(request_id: str) -> None:
    if not request_id:
        raise ValueError("PayPal request ids cannot be empty.")
    if len(request_id) > MAX_REQUEST_ID_LENGTH:
        raise ValueError(f"PayPal request ids must be at most {MAX_REQUEST_ID_LENGTH} characters.")
    if not request_id.isascii() or not request_id.isprintable():
        raise ValueError("PayPal request ids must be printable ASCII.")


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None


def _as_float(value: object, *, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
