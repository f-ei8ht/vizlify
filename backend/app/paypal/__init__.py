"""PayPal integration: one client, chosen from the configured mode."""

from app.core.config import Settings
from app.paypal.client import PayPalClient, PayPalConfig, PayPalResponse, new_request_id
from app.paypal.errors import (
    PayPalAuthError,
    PayPalError,
    PayPalRateLimited,
    PayPalRejectedError,
    PayPalUnavailable,
)
from app.paypal.mock import build_mock_transport

__all__ = [
    "PayPalAuthError",
    "PayPalClient",
    "PayPalConfig",
    "PayPalError",
    "PayPalRateLimited",
    "PayPalRejectedError",
    "PayPalResponse",
    "PayPalUnavailable",
    "build_client",
    "build_mock_transport",
    "new_request_id",
]


def build_client(settings: Settings) -> PayPalClient:
    if settings.PAYPAL_MODE == "mock":
        return PayPalClient(PayPalConfig.mock(), transport=build_mock_transport())
    return PayPalClient(PayPalConfig.from_settings(settings))
