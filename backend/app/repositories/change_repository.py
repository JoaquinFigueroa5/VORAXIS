from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, nulls_last, select, text
from sqlalchemy.orm import Session

from app.models.change_event import ChangeEvent
from app.models.change_metric import ChangeMetric

SORTS = {
    "area": lambda: nulls_last(ChangeEvent.area_km2.desc()),
    "score": lambda: nulls_last(ChangeEvent.change_score.desc()),
    "newest": lambda: ChangeEvent.created_at.desc(),
}

_MVT = text(
    """
    WITH bounds AS (
        SELECT ST_TileEnvelope(:z, :x, :y) AS mercator,
               ST_Transform(ST_TileEnvelope(:z, :x, :y), 4326) AS lonlat
    ),
    features AS (
        SELECT ST_AsMVTGeom(ST_Transform(c.geometry, 3857), bounds.mercator, 4096, 64, true) AS geom,
               c.id::text AS id,
               c.change_type,
               c.direction,
               round(c.change_score::numeric, 3)::float AS change_score,
               round(c.area_km2::numeric, 4)::float AS area_km2,
               round(c.mean_change_db::numeric, 2)::float AS mean_change_db
        FROM analysis.change_events AS c, bounds
        WHERE c.job_id = :job_id AND c.geometry && bounds.lonlat
    )
    SELECT ST_AsMVT(features, 'changes', 4096, 'geom') FROM features WHERE geom IS NOT NULL
    """
)


class ChangeRepository:
    def _stmt(self):
        return select(ChangeEvent, func.ST_AsGeoJSON(ChangeEvent.geometry).label("geojson"))

    @staticmethod
    def _filter(
        stmt,
        *,
        job_id=None,
        bbox: tuple[float, float, float, float] | None = None,
        change_type: Sequence[str] | None = None,
        direction: str | None = None,
        min_score: float | None = None,
        min_area_km2: float | None = None,
    ):
        if job_id:
            stmt = stmt.where(ChangeEvent.job_id == job_id)
        if bbox:
            stmt = stmt.where(
                func.ST_Intersects(ChangeEvent.geometry, func.ST_MakeEnvelope(*bbox, 4326))
            )
        if change_type:
            stmt = stmt.where(ChangeEvent.change_type.in_([value.upper() for value in change_type]))
        if direction:
            stmt = stmt.where(ChangeEvent.direction == direction.upper())
        if min_score is not None:
            stmt = stmt.where(ChangeEvent.change_score >= min_score)
        if min_area_km2 is not None:
            stmt = stmt.where(ChangeEvent.area_km2 >= min_area_km2)
        return stmt

    def list(
        self, db: Session, *, sort: str = "area", limit: int = 100, offset: int = 0, **filters
    ) -> Sequence[Any]:
        stmt = self._filter(self._stmt(), **filters)
        stmt = stmt.order_by(SORTS.get(sort, SORTS["area"])(), ChangeEvent.id)
        return db.execute(stmt.limit(limit).offset(offset)).all()

    def count(self, db: Session, **filters) -> int:
        stmt = self._filter(select(func.count()).select_from(ChangeEvent), **filters)
        return db.execute(stmt).scalar_one()

    def features(
        self,
        db: Session,
        *,
        tolerance_degrees: float = 0.0,
        sort: str = "area",
        limit: int = 2000,
        **filters,
    ) -> Sequence[Any]:
        """Rows for a GeoJSON layer; geometry simplified for the zoom it will be drawn at."""
        geometry = ChangeEvent.geometry
        if tolerance_degrees > 0:
            geometry = func.ST_SimplifyPreserveTopology(geometry, tolerance_degrees)
        stmt = self._filter(
            select(ChangeEvent, func.ST_AsGeoJSON(geometry, 5).label("geojson")), **filters
        )
        stmt = stmt.order_by(SORTS.get(sort, SORTS["area"])(), ChangeEvent.id)
        return db.execute(stmt.limit(limit)).all()

    def vector_tile(self, db: Session, job_id, z: int, x: int, y: int) -> bytes:
        tile = db.execute(_MVT, {"job_id": job_id, "z": z, "x": x, "y": y}).scalar()
        return bytes(tile) if tile else b""

    def get(self, db: Session, change_id) -> Any | None:
        return db.execute(self._stmt().where(ChangeEvent.id == change_id)).first()

    def metrics(self, db: Session, change_id) -> Sequence[ChangeMetric]:
        return (
            db.execute(
                select(ChangeMetric)
                .where(ChangeMetric.change_event_id == change_id)
                .order_by(ChangeMetric.metric_name)
            )
            .scalars()
            .all()
        )

    def add_metric(
        self,
        db: Session,
        *,
        change_event_id,
        metric_name: str,
        value: float | None,
        unit: str | None = None,
        source: str | None = None,
        metadata: dict | None = None,
    ) -> ChangeMetric:
        metric = ChangeMetric(
            change_event_id=change_event_id,
            metric_name=metric_name,
            value=value,
            unit=unit,
            source=source,
            extra_metadata=metadata,
        )
        db.add(metric)
        db.flush()
        return metric

    def delete_for_job(self, db: Session, job_id) -> None:
        for change in db.execute(
            select(ChangeEvent).where(ChangeEvent.job_id == job_id)
        ).scalars():
            db.delete(change)
        db.flush()

    def total_area_km2(self, db: Session) -> float:
        return float(db.execute(select(func.coalesce(func.sum(ChangeEvent.area_km2), 0.0))).scalar_one())
