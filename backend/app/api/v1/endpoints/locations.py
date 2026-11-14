import uuid

from fastapi import APIRouter

from app.dependencies import DbSession, Limit, Offset
from app.schemas.location import LocationOut
from app.services.location_service import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])
service = LocationService()


@router.get("", response_model=list[LocationOut])
def list_locations(db: DbSession, limit: Limit = 50, offset: Offset = 0) -> list[LocationOut]:
    return service.list(db, limit=limit, offset=offset)


# Declared before /{location_id} so "search" is not parsed as a UUID.
@router.get("/search", response_model=list[LocationOut])
def search_locations(q: str, db: DbSession, limit: Limit = 20) -> list[LocationOut]:
    return service.search(db, q, limit=limit)


@router.get("/{location_id}", response_model=LocationOut)
def get_location(location_id: uuid.UUID, db: DbSession) -> LocationOut:
    return service.get(db, location_id)
