from fastapi import APIRouter, Query

from app.dependencies import DbSession, Limit, Offset
from app.schemas.evidence import AuxiliaryEventOut
from app.services.auxiliary_service import AuxiliaryService
from app.utils.geometry import parse_bbox

router = APIRouter(prefix="/auxiliary", tags=["auxiliary"])
service = AuxiliaryService()


@router.get("/events", response_model=list[AuxiliaryEventOut])
def list_events(
    db: DbSession,
    source: str | None = None,
    event_type: str | None = None,
    bbox: str | None = Query(None, description="minx,miny,maxx,maxy"),
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[AuxiliaryEventOut]:
    return service.list(
        db,
        source=source,
        event_type=event_type,
        bbox=parse_bbox(bbox) if bbox else None,
        limit=limit,
        offset=offset,
    )
