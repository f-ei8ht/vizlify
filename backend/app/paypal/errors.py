"""PayPal failures, translated into the API's error envelope.

Messages stay generic on purpose: PayPal's raw body can echo request data, so
only the stable error name and `debug_id` are exposed. The rest is logged.
"""

from __future__ import annotations

from app.core.errors import AppError, ErrorCode


class PayPalError(AppError):
    code = ErrorCode.INTEGRATION_ERROR

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_name: str | None = None,
        debug_id: str | None = None,
    ) -> None:
        details: list[dict] = []
        if error_name:
            details.append({"field": "paypal_error", "message": error_name})
        if debug_id:
            details.append({"field": "debug_id", "message": debug_id})
        super().__init__(message, details or None)
        self.status_code = status_code
        self.error_name = error_name
        self.debug_id = debug_id


class PayPalAuthError(PayPalError):
    """Bad credentials, expired token after a refresh, or missing API features."""


class PayPalRejectedError(PayPalError):
    """PayPal refused a well-formed request; retrying it will not help."""


class PayPalRateLimited(PayPalError):
    """PayPal is throttling us and the retries are spent."""


class PayPalUnavailable(PayPalError):
    """Network failure, timeout, or 5xx after the retries are spent."""
