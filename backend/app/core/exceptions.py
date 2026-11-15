"""Application errors. Domain code raises these; the API maps them to HTTP.

The envelope carries a stable `code` (plus optional `params`) so the client can
write the message in its own language; `detail` stays as the untranslated
diagnostic for logs and the scientific view.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code or type(self).code
        self.params = params
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class IncompatibleObservationsError(AppError):
    status_code = 422
    code = "observations_incompatible"


class ProcessingError(AppError):
    status_code = 500
    code = "processing_failed"


class UpstreamError(AppError):
    """An external catalogue (ASF, USGS, POWER, FIRMS) failed or is not configured."""

    status_code = 502
    code = "upstream_failed"


class NotImplementedFeature(AppError):
    """Endpoint or mode that exists in the architecture but has no implementation yet."""

    status_code = 501
    code = "not_implemented"


def _envelope(exc: AppError) -> dict[str, Any]:
    return {
        "error": type(exc).__name__,
        "code": exc.code,
        "params": exc.params,
        "detail": exc.message,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_envelope(exc))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic messages are English prose: send the field names, not the text.
        fields = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": "ValidationError",
                "code": "validation_failed",
                "params": {"fields": fields},
                "detail": "request validation failed",
            },
        )
