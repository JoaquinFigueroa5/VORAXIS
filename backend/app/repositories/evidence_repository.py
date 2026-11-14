from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, nulls_last, select
from sqlalchemy.orm import Session

from app.models.auxiliary_event import AuxiliaryEvent
from app.models.evidence_record import EvidenceRecord


class EvidenceRepository:
    def for_change(self, db: Session, change_id) -> Sequence[Any]:
        stmt = (
            select(
                EvidenceRecord,
                AuxiliaryEvent,
                func.ST_AsGeoJSON(AuxiliaryEvent.geometry).label("geojson"),
            )
            .join(AuxiliaryEvent, EvidenceRecord.auxiliary_event_id == AuxiliaryEvent.id)
            .where(EvidenceRecord.change_event_id == change_id)
            .order_by(nulls_last(EvidenceRecord.evidence_score.desc()))
        )
        return db.execute(stmt).all()

    def list_auxiliary(
        self,
        db: Session,
        *,
        source: str | None = None,
        event_type: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Any]:
        stmt = select(
            AuxiliaryEvent, func.ST_AsGeoJSON(AuxiliaryEvent.geometry).label("geojson")
        )
        if source:
            stmt = stmt.where(AuxiliaryEvent.source == source.upper())
        if event_type:
            stmt = stmt.where(AuxiliaryEvent.event_type == event_type.upper())
        if bbox:
            stmt = stmt.where(
                func.ST_Intersects(AuxiliaryEvent.geometry, func.ST_MakeEnvelope(*bbox, 4326))
            )
        stmt = stmt.order_by(AuxiliaryEvent.event_date.desc()).limit(limit).offset(offset)
        return db.execute(stmt).all()

    def add(
        self,
        db: Session,
        *,
        change_event_id,
        auxiliary_event_id,
        spatial_relation: str,
        distance_km: float | None,
        time_difference_hours: float | None,
        evidence_score: float | None,
        explanation: str,
    ) -> EvidenceRecord:
        record = EvidenceRecord(
            change_event_id=change_event_id,
            auxiliary_event_id=auxiliary_event_id,
            spatial_relation=spatial_relation,
            distance_km=distance_km,
            time_difference_hours=time_difference_hours,
            evidence_score=evidence_score,
            explanation=explanation,
        )
        db.add(record)
        db.flush()
        return record

    def add_auxiliary(
        self,
        db: Session,
        *,
        source: str,
        external_id: str | None,
        event_type: str,
        event_date,
        longitude: float,
        latitude: float,
        magnitude: float | None = None,
        metadata: dict | None = None,
    ) -> AuxiliaryEvent:
        event = AuxiliaryEvent(
            source=source,
            external_id=external_id,
            event_type=event_type,
            event_date=event_date,
            geometry=func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
            magnitude=magnitude,
            extra_metadata=metadata,
        )
        db.add(event)
        db.flush()
        return event

    def find_auxiliary(self, db: Session, *, source: str, external_id: str):
        return db.execute(
            select(AuxiliaryEvent).where(
                AuxiliaryEvent.source == source,
                AuxiliaryEvent.external_id == external_id,
            )
        ).scalar_one_or_none()

    def count(self, db: Session) -> int:
        return db.execute(select(func.count()).select_from(EvidenceRecord)).scalar_one()

    def count_auxiliary(self, db: Session) -> int:
        return db.execute(select(func.count()).select_from(AuxiliaryEvent)).scalar_one()
