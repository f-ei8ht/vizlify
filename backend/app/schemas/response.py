from typing import Any

from pydantic import BaseModel


class ApiError(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ApiResponse[DataT](BaseModel):
    """The single envelope every endpoint returns.

    Success carries `data`; failure carries `error`. The HTTP status code is
    the source of truth for status, so it is deliberately not duplicated here.
    """

    data: DataT | None = None
    error: ApiError | None = None


def success[DataT](data: DataT | None = None) -> ApiResponse[DataT]:
    return ApiResponse(data=data)


def error(code: str, message: str, details: list[dict[str, Any]] | None = None) -> ApiResponse[Any]:
    return ApiResponse(error=ApiError(code=code, message=message, details=details))
