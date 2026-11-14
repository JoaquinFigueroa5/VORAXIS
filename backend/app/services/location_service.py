from collections.abc import Sequence

from app.core.exceptions import NotFoundError
from app.repositories.location_repository import LocationRepository
from app.schemas.location import LocationOut
from app.utils.geometry import as_geojson


class LocationService:
    def __init__(self, repo: LocationRepository | None = None) -> None:
        self.repo = repo or LocationRepository()

    @staticmethod
    def _to_out(row) -> LocationOut:
        location, geojson = row
        return LocationOut(
            id=location.id,
            name=location.name,
            country=location.country,
            description=location.description,
            geometry=as_geojson(geojson),
            created_at=location.created_at,
        )

    def list(self, db, limit: int = 50, offset: int = 0) -> list[LocationOut]:
        return [self._to_out(row) for row in self.repo.list(db, limit=limit, offset=offset)]

    def search(self, db, query: str, limit: int = 20) -> Sequence[LocationOut]:
        return [self._to_out(row) for row in self.repo.search(db, query, limit=limit)]

    def get(self, db, location_id) -> LocationOut:
        row = self.repo.get(db, location_id)
        if row is None:
            raise NotFoundError(f"location {location_id} not found")
        return self._to_out(row)
