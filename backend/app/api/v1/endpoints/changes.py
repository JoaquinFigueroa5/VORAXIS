import uuid

from fastapi import APIRouter, Query

from app.dependencies import DbSession, Limit, Offset
from app.schemas.change import ChangeEventOut, ChangeMetricOut
from app.services.change_service import ChangeService
from app.utils.geometry import parse_bbox

router = APIRouter(prefix="/changes", tags=["changes"])
service = ChangeService()


@router.get("", response_model=list[ChangeEventOut])
def list_changes(
    db: DbSession,
    job_id: uuid.UUID | None = None,
    bbox: str | None = Query(None, description="minx,miny,maxx,maxy"),
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[ChangeEventOut]:
    return service.list(
        db,
        job_id=job_id,
        bbox=parse_bbox(bbox) if bbox else None,
        limit=limit,
        offset=offset,
    )


@router.get("/{change_id}", response_model=ChangeEventOut)
def get_change(change_id: uuid.UUID, db: DbSession) -> ChangeEventOut:
    return service.get(db, change_id)


@router.get("/{change_id}/metrics", response_model=list[ChangeMetricOut])
def get_metrics(change_id: uuid.UUID, db: DbSession) -> list[ChangeMetricOut]:
    return service.metrics(db, change_id)

