from typing import Any

from sqlalchemy import case, func, select

from app.core.exceptions import NotFoundError
from app.core.exceptions import NotFoundError
from app.models.auxiliary_event import AuxiliaryEvent
from app.models.change_event import ChangeEvent
from app.models.evidence_record import EvidenceRecord
from app.models.location import Location
from app.models.observation import Observation
from app.models.processing_job import ProcessingJob
from app.repositories.change_repository import ChangeRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.job_repository import JobRepository
from app.repositories.nisar_repository import NisarRepository
from app.repositories.observation_repository import ObservationRepository
from app.schemas.common import InsightsOut

SCORE_BINS = 10
AREA_BINS_KM2 = (0.05, 0.1, 0.5, 1.0, 5.0)


class InsightsService:
    def summary(self, db) -> InsightsOut:
        area = func.coalesce(func.sum(ChangeEvent.area_km2), 0.0)
        # Distributions stay empty until there is something to distribute: the client
        # shows "not enough data" instead of inventing a chart.
        by_type = [
            {
                "change_type": change_type,
                "count": count,
                "area_km2": round(total or 0.0, 3),
            }
            for change_type, count, total in db.execute(
                select(ChangeEvent.change_type, func.count(), area)
                .group_by(ChangeEvent.change_type)
                .order_by(func.count().desc())
            )
        ]
        by_direction = [
            {"direction": direction, "count": count, "area_km2": round(total or 0.0, 3)}
            for direction, count, total in db.execute(
                select(ChangeEvent.direction, func.count(), area).group_by(ChangeEvent.direction)
            )
        ]
        by_month = [
            {"month": month, "count": count, "area_km2": round(total or 0.0, 3)}
            for month, count, total in db.execute(
                select(
                    func.to_char(ChangeEvent.created_at, "YYYY-MM").label("month"),
                    func.count(),
                    area,
                )
                .group_by("month")
                .order_by("month")
            )
        ]
        by_location = [
            {
                "location_id": str(location_id),
                "name": name,
                "count": count,
                "area_km2": round(total or 0.0, 3),
            }
            for location_id, name, count, total in db.execute(
                select(Location.id, Location.name, func.count(), area)
                .join(ProcessingJob, ProcessingJob.location_id == Location.id)
                .join(ChangeEvent, ChangeEvent.job_id == ProcessingJob.id)
                .group_by(Location.id, Location.name)
                .order_by(func.count().desc())
            )
        ]
        return InsightsOut(
            locations=db.execute(select(func.count()).select_from(Location)).scalar_one(),
            scenes=NisarRepository().count(db),
            observations=ObservationRepository().count(db),
            jobs=JobRepository().count_by_status(db),
            change_events=ChangeRepository().count(db),
            change_area_km2=round(ChangeRepository().total_area_km2(db), 3),
            evidence_records=EvidenceRepository().count(db),
            auxiliary_events=EvidenceRepository().count_auxiliary(db),
            by_type=by_type,
            by_direction=by_direction,
            by_month=by_month,
            by_location=by_location,
        )

    def for_job(self, db, job_id) -> dict[str, Any]:
        """Everything the charts of one analysis need, aggregated in the database."""
        job = db.get(ProcessingJob, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        mine = ChangeEvent.job_id == job.id
        area = func.coalesce(func.sum(ChangeEvent.area_km2), 0.0)

        totals = db.execute(
            select(
                func.count(),
                area,
                func.avg(ChangeEvent.change_score),
                func.max(ChangeEvent.change_score),
                func.max(ChangeEvent.area_km2),
            ).where(mine)
        ).one()

        by_type = [
            {
                "change_type": change_type,
                "count": count,
                "area_km2": round(float(total), 3),
                "mean_score": None if score is None else round(float(score), 3),
                "mean_change_db": None if change is None else round(float(change), 2),
            }
            for change_type, count, total, score, change in db.execute(
                select(
                    ChangeEvent.change_type,
                    func.count(),
                    area,
                    func.avg(ChangeEvent.change_score),
                    func.avg(ChangeEvent.mean_change_db),
                )
                .where(mine)
                .group_by(ChangeEvent.change_type)
                .order_by(area.desc())
            )
        ]

        by_direction = [
            {"direction": direction, "count": count, "area_km2": round(float(total), 3)}
            for direction, count, total in db.execute(
                select(ChangeEvent.direction, func.count(), area)
                .where(mine)
                .group_by(ChangeEvent.direction)
                .order_by(area.desc())
            )
        ]

        score_bin = func.least(
            func.floor(func.coalesce(ChangeEvent.change_score, 0.0) * SCORE_BINS), SCORE_BINS - 1
        )
        score_counts = dict(
            db.execute(select(score_bin, func.count()).where(mine).group_by(score_bin)).all()
        )
        score_histogram = [
            {
                "from": round(index / SCORE_BINS, 2),
                "to": round((index + 1) / SCORE_BINS, 2),
                "count": int(score_counts.get(index, 0)),
            }
            for index in range(SCORE_BINS)
        ]

        area_bin = case(
            *[(ChangeEvent.area_km2 < edge, index) for index, edge in enumerate(AREA_BINS_KM2)],
            else_=len(AREA_BINS_KM2),
        )
        area_rows = {
            index: (count, total)
            for index, count, total in db.execute(
                select(area_bin, func.count(), area).where(mine).group_by(area_bin)
            )
        }
        edges = (0.0, *AREA_BINS_KM2, None)
        area_histogram = [
            {
                "from_km2": edges[index],
                "to_km2": edges[index + 1],
                "count": int(area_rows.get(index, (0, 0))[0]),
                "area_km2": round(float(area_rows.get(index, (0, 0))[1]), 3),
            }
            for index in range(len(AREA_BINS_KM2) + 1)
        ]

        linked = (
            select(EvidenceRecord.auxiliary_event_id, EvidenceRecord.evidence_score)
            .join(ChangeEvent, ChangeEvent.id == EvidenceRecord.change_event_id)
            .where(mine)
            .subquery()
        )
        evidence = [
            {
                "event_type": event_type,
                "source": source,
                "events": events,
                "links": links,
                "best_score": None if best is None else round(float(best), 3),
            }
            for event_type, source, events, links, best in db.execute(
                select(
                    AuxiliaryEvent.event_type,
                    AuxiliaryEvent.source,
                    func.count(func.distinct(AuxiliaryEvent.id)),
                    func.count(),
                    func.max(linked.c.evidence_score),
                )
                .join(linked, linked.c.auxiliary_event_id == AuxiliaryEvent.id)
                .group_by(AuxiliaryEvent.event_type, AuxiliaryEvent.source)
            )
        ]

        rain_ids = (
            select(func.distinct(linked.c.auxiliary_event_id))
            .join(AuxiliaryEvent, AuxiliaryEvent.id == linked.c.auxiliary_event_id)
            .where(AuxiliaryEvent.event_type == "PRECIPITATION")
        )
        precipitation = []
        for event, lon, lat in db.execute(
            select(
                AuxiliaryEvent,
                func.ST_X(func.ST_Centroid(AuxiliaryEvent.geometry)),
                func.ST_Y(func.ST_Centroid(AuxiliaryEvent.geometry)),
            )
            .where(AuxiliaryEvent.id.in_(rain_ids))
            .order_by(AuxiliaryEvent.magnitude.desc())
        ):
            meta = event.extra_metadata or {}
            precipitation.append(
                {
                    "cell_center": {"longitude": round(lon, 3), "latitude": round(lat, 3)},
                    "total_mm": event.magnitude,
                    "expected_mm": meta.get("expected_mm"),
                    "anomaly_pct": meta.get("anomaly_pct"),
                    "max_daily_mm": meta.get("max_daily_mm"),
                    "peak_date": meta.get("peak_date"),
                    "series": [
                        {"date": day, "mm": value}
                        for day, value in (meta.get("daily_mm") or {}).items()
                    ],
                }
            )

        before = db.get(Observation, job.before_observation_id)
        after = db.get(Observation, job.after_observation_id)
        result = job.result or {}
        return {
            "job_id": str(job.id),
            "status": job.status,
            "acquisitions": {
                "before": None if before is None else before.acquisition_date.isoformat(),
                "after": None if after is None else after.acquisition_date.isoformat(),
            },
            "totals": {
                "changes": totals[0],
                "area_km2": round(float(totals[1]), 3),
                "mean_score": None if totals[2] is None else round(float(totals[2]), 3),
                "max_score": totals[3],
                "largest_km2": totals[4],
                "threshold_db": result.get("threshold_db"),
                "valid_pixel_percentage": result.get("valid_pixel_percentage"),
                "aoi_coverage_percentage": result.get("aoi_coverage_percentage"),
            },
            "by_type": by_type,
            "by_direction": by_direction,
            "score_histogram": score_histogram,
            "area_histogram": area_histogram,
            "evidence": evidence,
            "precipitation": precipitation,
            "sources": result.get("evidence_sources") or {},
            "warnings": result.get("warnings") or [],
        }
