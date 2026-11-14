"""NASA FIRMS active-fire detections.

Contract only: the area API needs a MAP_KEY and returns CSV, which is a separate
ingestion job. Deliberately not half-implemented (docs/architecture.md, rule 5).
"""

from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.exceptions import AppError, NotImplementedFeature


class FirmsClient:
    @property
    def configured(self) -> bool:
        return bool(settings.firms_api_key)

    def fetch_events(
        self, *, bbox: tuple[float, float, float, float], start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        if not self.configured:
            raise AppError("FIRMS_API_KEY is not set")
        raise NotImplementedFeature("FIRMS ingestion is not implemented yet")
