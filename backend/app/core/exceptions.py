"""Application errors. Domain code raises these; the API maps them to HTTP."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class IncompatibleObservationsError(AppError):
    status_code = 422


class ProcessingError(AppError):
    status_code = 500


class UpstreamError(AppError):
    """An external catalogue (ASF, USGS, POWER, FIRMS) failed or is not configured."""

    status_code = 502


class NotImplementedFeature(AppError):
    """Endpoint or mode that exists in the architecture but has no implementation yet."""

    status_code = 501


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": type(exc).__name__, "detail": exc.message},
        )
