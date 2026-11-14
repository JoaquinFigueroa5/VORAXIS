import uuid

from fastapi import APIRouter, Query

from app.dependencies import DbSession, Limit, Offset
from app.schemas.nisar import NisarSceneOut
from app.services.nisar_service import NisarService
from app.utils.geometry import parse_bbox
from app.utils.validators import ensure_date_range

router = APIRouter(prefix="/nisar", tags=["nisar"])
service = NisarService()


@router.get("/scenes", response_model=list[NisarSceneOut])
def list_scenes(
    db: DbSession,
    product_type: str | None = None,
    maturity: str | None = None,
    start: str | None = Query(None, description="ISO date/time lower bound"),
    end: str | None = Query(None, description="ISO date/time upper bound"),
    bbox: str | None = Query(None, description="minx,miny,maxx,maxy"),
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[NisarSceneOut]:
    start_dt, end_dt = ensure_date_range(start, end)
    return service.list(
        db,
        product_type=product_type,
        maturity=maturity,
        start=start_dt,
        end=end_dt,
        bbox=parse_bbox(bbox) if bbox else None,
        limit=limit,
        offset=offset,
    )


@router.get("/scenes/{scene_id}", response_model=NisarSceneOut)
def get_scene(scene_id: uuid.UUID, db: DbSession) -> NisarSceneOut:
    return service.get(db, scene_id)
