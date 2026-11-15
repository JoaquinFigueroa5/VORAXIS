import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Response

from app.dependencies import DbSession, Offset
from app.schemas.change import ChangeEventOut, ChangeMetricOut
from app.services.change_service import ChangeService
from app.services.interpretation_service import InterpretationService
from app.utils.geometry import parse_bbox

router = APIRouter(prefix="/changes", tags=["changes"])
service = ChangeService()
interpretation = InterpretationService()

Bbox = Annotated[str | None, Query(description="minx,miny,maxx,maxy")]
ChangeType = Annotated[
    list[str] | None,
    Query(description="Repeatable: change_type=POSSIBLE_FLOODING&change_type=POSSIBLE_BURN_SCAR"),
]
Direction = Annotated[Literal["DECREASE", "INCREASE"] | None, Query()]
MinScore = Annotated[float | None, Query(ge=0, le=1)]
MinArea = Annotated[float | None, Query(ge=0)]
Sort = Annotated[Literal["area", "score", "newest"], Query()]


def _filters(job_id, bbox, change_type, direction, min_score, min_area_km2) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "bbox": parse_bbox(bbox) if bbox else None,
        "change_type": change_type,
        "direction": direction,
        "min_score": min_score,
        "min_area_km2": min_area_km2,
    }


@router.get("", response_model=list[ChangeEventOut])
def list_changes(
    response: Response,
    db: DbSession,
    job_id: uuid.UUID | None = None,
    bbox: Bbox = None,
    change_type: ChangeType = None,
    direction: Direction = None,
    min_score: MinScore = None,
    min_area_km2: MinArea = None,
    sort: Sort = "area",
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Offset = 0,
) -> list[ChangeEventOut]:
    """One page of changes. The total that matches the filters is in `X-Total-Count`."""
    filters = _filters(job_id, bbox, change_type, direction, min_score, min_area_km2)
    response.headers["X-Total-Count"] = str(service.count(db, **filters))
    return service.list(db, sort=sort, limit=limit, offset=offset, **filters)


# Declared before /{change_id} so "geojson" is not parsed as a UUID.
@router.get("/geojson")
def changes_geojson(
    db: DbSession,
    job_id: uuid.UUID | None = None,
    bbox: Bbox = None,
    change_type: ChangeType = None,
    direction: Direction = None,
    min_score: MinScore = None,
    min_area_km2: MinArea = None,
    sort: Sort = "area",
    zoom: Annotated[
        float | None, Query(ge=0, le=22, description="Map zoom: simplifies geometry to one pixel")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 2000,
) -> dict[str, Any]:
    """Changes as a GeoJSON FeatureCollection for a map layer (no geometry in properties)."""
    filters = _filters(job_id, bbox, change_type, direction, min_score, min_area_km2)
    return service.geojson(db, zoom=zoom, limit=limit, sort=sort, **filters)


@router.get("/{change_id}", response_model=ChangeEventOut)
def get_change(change_id: uuid.UUID, db: DbSession) -> ChangeEventOut:
    return service.get(db, change_id)


@router.get("/{change_id}/metrics", response_model=list[ChangeMetricOut])
def get_metrics(change_id: uuid.UUID, db: DbSession) -> list[ChangeMetricOut]:
    return service.metrics(db, change_id)


@router.get("/{change_id}/interpretation")
def get_interpretation(change_id: uuid.UUID, db: DbSession) -> dict[str, Any]:
    """What was measured, what it suggests, which sources answered and what is missing."""
    return interpretation.for_change(db, change_id)
