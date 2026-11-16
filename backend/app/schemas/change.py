import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class ChangeEventOut(ORMModel):
    id: uuid.UUID
    job_id: uuid.UUID
    change_type: str
    geometry: dict[str, Any]
    area_km2: float | None = None
    change_score: float | None = None
    valid_pixel_percentage: float | None = None
    direction: str | None = None  # DECREASE | INCREASE
    mean_change_db: float | None = None
    # {type, confidence, reasons: [{code, params}]}: tentative, never a probability.
    classification: dict[str, Any] | None = None
    created_at: datetime


class ChangeMetricOut(ORMModel):
    id: uuid.UUID
    change_event_id: uuid.UUID
    metric_name: str
    value: float | None = None
    unit: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None
