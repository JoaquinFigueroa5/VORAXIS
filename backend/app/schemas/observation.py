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
    # Read through the scene so the client can label and filter without extra calls.
    product_id: str | None = None
    product_type: str | None = None
    maturity: str | None = None
    orbit_direction: str | None = None
    polarization: list[str] | None = None
    created_at: datetime
