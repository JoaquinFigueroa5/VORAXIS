import uuid

from fastapi import APIRouter

from app.dependencies import DbSession, Limit, Offset
from app.schemas.observation import ObservationOut
from app.services.observation_service import ObservationService

router = APIRouter(prefix="/observations", tags=["observations"])
service = ObservationService()


@router.get("", response_model=list[ObservationOut])
def list_observations(
    db: DbSession,
    scene_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    storage_status: str | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[ObservationOut]:
    return service.list(
        db,
        scene_id=scene_id,
        location_id=location_id,
        storage_status=storage_status,
        limit=limit,
        offset=offset,
    )


@router.get("/{observation_id}", response_model=ObservationOut)
def get_observation(observation_id: uuid.UUID, db: DbSession) -> ObservationOut:
    return service.get(db, observation_id)
