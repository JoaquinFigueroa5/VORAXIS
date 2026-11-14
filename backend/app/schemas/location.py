import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class LocationOut(ORMModel):
    id: uuid.UUID
    name: str
    country: str | None = None
    description: str | None = None
    geometry: dict[str, Any]
    created_at: datetime
