import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class ObservationOut(ORMModel):
    id: uuid.UUID
    scene_id: uuid.UUID
    location_id: uuid.UUID | None = None
    acquisition_date: datetime
    processing_version: str | None = None
    storage_status: str
    created_at: datetime
