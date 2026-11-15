from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GeoJSON(BaseModel):
    type: str
    coordinates: list[Any] | None = None


class HealthOut(BaseModel):
    status: str
    database: bool
    redis: bool
    version: str


class ErrorOut(BaseModel):
    error: str
    detail: str


class InsightsOut(BaseModel):
    locations: int
    scenes: int
    observations: int
    jobs: dict[str, int]
    change_events: int
    change_area_km2: float
    evidence_records: int
    auxiliary_events: int
    # Distributions across every analysis; empty when nothing has been detected yet.
    by_type: list[dict[str, Any]] = []
    by_direction: list[dict[str, Any]] = []
    by_month: list[dict[str, Any]] = []
    by_location: list[dict[str, Any]] = []
