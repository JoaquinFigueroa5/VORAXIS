from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.api.v1.endpoints.health import VERSION
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    try:
        from app.core.storage import ensure_bucket

        ensure_bucket()
    except Exception as exc:  # MinIO down must not stop the API from serving metadata
        logger.warning("could not ensure MinIO bucket: %s", exc)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=VERSION,
        lifespan=lifespan,
        description="NISAR change detection: catalogue, analysis jobs, changes and evidence.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "docs": "/docs", "api": settings.api_prefix}

    return app


app = create_app()
