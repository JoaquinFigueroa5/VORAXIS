import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LocationOut(ORMModel):
    id: uuid.UUID
    name: str
    country: str | None = None
    description: str | None = None
    geometry: dict[str, Any]
    created_at: datetime


class LocationCreate(BaseModel):
    """An area of interest drawn on the map: a GeoJSON polygon, or a bounding box."""

    name: str = Field(min_length=1, max_length=150)
    country: str | None = Field(default=None, max_length=100)
    description: str | None = None
    # GeoJSON Polygon or MultiPolygon in EPSG:4326 (a Feature is accepted too).
    geometry: dict[str, Any] | None = None
    # Alternative to `geometry`: [west, south, east, north].
    bbox: tuple[float, float, float, float] | None = None
