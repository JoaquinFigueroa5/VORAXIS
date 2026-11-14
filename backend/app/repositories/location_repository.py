from typing import Any

from sqlalchemy import Sequence, func, select
from sqlalchemy.orm import Session

from app.models.location import Location


class LocationRepository:
    def _stmt(self):
        return select(Location, func.ST_AsGeoJSON(Location.geometry).label("geojson"))

    def list(self, db: Session, limit: int = 50, offset: int = 0) -> Sequence[Any]:
        return db.execute(self._stmt().order_by(Location.name).limit(limit).offset(offset)).all()

    def search(self, db: Session, query: str, limit: int = 20) -> Sequence[Any]:
        stmt = self._stmt().where(Location.name.ilike(f"%{query}%")).order_by(Location.name)
        return db.execute(stmt.limit(limit)).all()

    def get(self, db: Session, location_id) -> Any | None:
        return db.execute(self._stmt().where(Location.id == location_id)).first()

    def get_model(self, db: Session, location_id) -> Location | None:
        return db.get(Location, location_id)

    def get_model_by_name(self, db: Session, name: str) -> Location | None:
        return db.execute(select(Location).where(Location.name == name)).scalar_one_or_none()

    def create(
        self,
        db: Session,
        *,
        name: str,
        country: str | None,
        description: str | None,
        geometry_wkt: str,
    ) -> Location:
        location = Location(
            name=name,
            country=country,
            description=description,
            geometry=func.ST_GeomFromText(geometry_wkt, 4326),
        )
        db.add(location)
        db.commit()
        db.refresh(location)
        return location
