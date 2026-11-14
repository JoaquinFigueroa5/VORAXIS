from fastapi import APIRouter
from sqlalchemy import text

from app.core.redis import get_redis
from app.dependencies import DbSession
from app.schemas.common import HealthOut

router = APIRouter(tags=["health"])

VERSION = "0.1.0"


@router.get("/health", response_model=HealthOut, summary="Service, database and queue status")
def health(db: DbSession) -> HealthOut:
    database_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_ok = False

    redis_ok = True
    try:
        get_redis().ping()
    except Exception:
        redis_ok = False

    return HealthOut(
        status="ok" if database_ok and redis_ok else "degraded",
        database=database_ok,
        redis=redis_ok,
        version=VERSION,
    )
