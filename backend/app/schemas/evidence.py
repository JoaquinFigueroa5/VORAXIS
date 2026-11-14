import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuxiliaryEventOut(ORMModel):
    id: uuid.UUID
    source: str
    external_id: str | None = None
    event_type: str
    event_date: datetime
    geometry: dict[str, Any]
    magnitude: float | None = None
    metadata: dict[str, Any] | None = None


class EvidenceRecordOut(ORMModel):
    id: uuid.UUID
    change_event_id: uuid.UUID
    auxiliary_event_id: uuid.UUID
    spatial_relation: str
    distance_km: float | None = None
    time_difference_hours: float | None = None
    evidence_score: float | None = None
    explanation: str | None = None
    created_at: datetime
    event: AuxiliaryEventOut | None = None
