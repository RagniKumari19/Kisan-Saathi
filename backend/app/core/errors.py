"""Application error hierarchy mapped onto the documented JSON error contract."""
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

    def __init__(
        self,
        message: str = "Something went wrong.",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class AuthRequired(AppError):
    status_code = 401
    code = "AUTH_REQUIRED"


class InvalidCredentials(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"


class TokenExpired(AppError):
    status_code = 401
    code = "TOKEN_EXPIRED"


class RefreshReused(AppError):
    status_code = 401
    code = "REFRESH_REUSED"


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"


class PayloadTooLarge(AppError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"


class UnsupportedMediaType(AppError):
    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"


class ImageUnreadable(AppError):
    status_code = 422
    code = "IMAGE_UNREADABLE"


class NoLeafDetected(AppError):
    status_code = 422
    code = "NO_LEAF_DETECTED"


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"


class OtpInvalid(AppError):
    status_code = 400
    code = "OTP_INVALID"


class SmsUnavailable(AppError):
    status_code = 503
    code = "SMS_UNAVAILABLE"


class UpstreamUnavailable(AppError):
    status_code = 502
    code = "UPSTREAM_UNAVAILABLE"


class ModelUnavailable(AppError):
    status_code = 503
    code = "MODEL_UNAVAILABLE"


class NotImplementedYet(AppError):
    status_code = 501
    code = "NOT_IMPLEMENTED"


def error_body(code: str, message: str, details: list | None, request_id: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id,
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    headers = {}
    if isinstance(exc, RateLimited):
        headers["Retry-After"] = str(getattr(exc, "retry_after", 60))
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.details, request_id),
        headers=headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    details = [
        {
            "field": ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query")),
            "issue": err.get("msg", "invalid value"),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content=error_body("VALIDATION_ERROR", "One or more fields are invalid.", details, request_id),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=500,
        content=error_body("INTERNAL_ERROR", "An unexpected error occurred.", None, request_id),
    )
