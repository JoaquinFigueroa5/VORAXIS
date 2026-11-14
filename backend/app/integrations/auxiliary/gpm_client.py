"""GPM IMERG precipitation.

Contract only: IMERG is a gridded product; turning it into `auxiliary_events`
implies choosing an aggregation window and unit, which is a modelling decision
left to the evidence phase.
"""

from datetime import datetime
from typing import Any

from app.core.exceptions import NotImplementedFeature
from app.integrations.nisar.earthdata_client import EarthdataClient


class GpmClient:
    def __init__(self, earthdata: EarthdataClient | None = None) -> None:
        self.earthdata = earthdata or EarthdataClient()

    def fetch_events(
        self, *, bbox: tuple[float, float, float, float], start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        raise NotImplementedFeature("GPM/IMERG ingestion is not implemented yet")
