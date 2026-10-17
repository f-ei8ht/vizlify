from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.response import ApiError, ApiResponse


class ErrorCode(StrEnum):
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"


_STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL_ERROR: 500,
}

_CODE_BY_STATUS: dict[int, ErrorCode] = {status: code for code, status in _STATUS_BY_CODE.items()}


class AppError(Exception):
    code: ErrorCode = ErrorCode.BAD_REQUEST

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    code = ErrorCode.NOT_FOUND

    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found.")
        self.resource = resource


class ConflictError(AppError):
    code = ErrorCode.CONFLICT


def _envelope(
    code: ErrorCode,
    message: str,
    details: list[dict] | None = None,
) -> JSONResponse:
    payload = ApiResponse(error=ApiError(code=code.value, message=message, details=details))
    return JSONResponse(status_code=_STATUS_BY_CODE[code], content=payload.model_dump())


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return _envelope(exc.code, exc.message)


async def _handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    code = _CODE_BY_STATUS.get(exc.status_code, ErrorCode.BAD_REQUEST)
    if not isinstance(exc.detail, str):
        return _envelope(code, code.value.replace("_", " ").capitalize())
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(error=ApiError(code=code.value, message=exc.detail)).model_dump(),
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in issue["loc"]),
            "message": issue["msg"],
            "type": issue["type"],
        }
        for issue in exc.errors()
    ]
    return _envelope(ErrorCode.VALIDATION_ERROR, "Request validation failed.", details)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return _envelope(ErrorCode.INTERNAL_ERROR, "Something went wrong. Please try again.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(HTTPException, _handle_http_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
