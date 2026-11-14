import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class NisarSceneOut(ORMModel):
    id: uuid.UUID
    product_id: str
    product_type: str
    maturity: str | None = None
    acquisition_start: datetime
    acquisition_end: datetime | None = None
    orbit_direction: str | None = None
    polarization: list[str] | None = None
    footprint: dict[str, Any]
    source_url: str | None = None
    metadata: dict[str, Any] | None = None
    discovered_at: datetime
