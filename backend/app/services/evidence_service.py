from app.core.exceptions import NotFoundError
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.evidence import AuxiliaryEventOut, EvidenceRecordOut
from app.utils.geometry import as_geojson


class EvidenceService:
    def __init__(self, repo: EvidenceRepository | None = None) -> None:
        self.repo = repo or EvidenceRepository()

    def for_change(self, db, change_id) -> list[EvidenceRecordOut]:
        records = []
        for record, event, geojson in self.repo.for_change(db, change_id):
            records.append(
                EvidenceRecordOut(
                    id=record.id,
                    change_event_id=record.change_event_id,
                    auxiliary_event_id=record.auxiliary_event_id,
                    spatial_relation=record.spatial_relation,
                    distance_km=record.distance_km,
                    time_difference_hours=record.time_difference_hours,
                    evidence_score=record.evidence_score,
                    explanation=record.explanation,
                    created_at=record.created_at,
                    event=AuxiliaryEventOut(
                        id=event.id,
                        source=event.source,
                        external_id=event.external_id,
                        event_type=event.event_type,
                        event_date=event.event_date,
                        geometry=as_geojson(geojson),
                        magnitude=event.magnitude,
                        metadata=event.extra_metadata,
                    ),
                )
            )
        if not records:
            # Distinguish "no evidence" from "no such change".
            from app.repositories.change_repository import ChangeRepository

            if ChangeRepository().get(db, change_id) is None:
                raise NotFoundError(f"change {change_id} not found")
        return records

    def list_auxiliary(self, db, **filters) -> list[AuxiliaryEventOut]:
        return [
            AuxiliaryEventOut(
                id=event.id,
                source=event.source,
                external_id=event.external_id,
                event_type=event.event_type,
                event_date=event.event_date,
                geometry=as_geojson(geojson),
                magnitude=event.magnitude,
                metadata=event.extra_metadata,
            )
            for event, geojson in self.repo.list_auxiliary(db, **filters)
        ]
