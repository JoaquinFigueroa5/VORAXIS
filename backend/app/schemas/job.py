import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class JobOut(ORMModel):
    id: uuid.UUID
    location_id: uuid.UUID
    before_observation_id: uuid.UUID
    after_observation_id: uuid.UUID
    status: str
    progress: int
    current_step: str | None = None
    error_message: str | None = None
    parameters: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
