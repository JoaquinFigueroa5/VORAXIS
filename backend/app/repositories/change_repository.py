from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, nulls_last, select
from sqlalchemy.orm import Session

from app.models.change_event import ChangeEvent
from app.models.change_metric import ChangeMetric


class ChangeRepository:
    def _stmt(self):
        return select(ChangeEvent, func.ST_AsGeoJSON(ChangeEvent.geometry).label("geojson"))

    def list(
        self,
        db: Session,
        *,
        job_id=None,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Any]:
        stmt = self._stmt()
        if job_id:
            stmt = stmt.where(ChangeEvent.job_id == job_id)
        if bbox:
            stmt = stmt.where(
                func.ST_Intersects(ChangeEvent.geometry, func.ST_MakeEnvelope(*bbox, 4326))
            )
        stmt = stmt.order_by(nulls_last(ChangeEvent.area_km2.desc())).limit(limit).offset(offset)
        return db.execute(stmt).all()

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

    def count(self, db: Session) -> int:
        return db.execute(select(func.count()).select_from(ChangeEvent)).scalar_one()

    def total_area_km2(self, db: Session) -> float:
        return float(db.execute(select(func.coalesce(func.sum(ChangeEvent.area_km2), 0.0))).scalar_one())
