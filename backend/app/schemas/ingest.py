import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Download NISAR GCOV products and prepare them for analysis over a location."""

    location_id: uuid.UUID
    # Granule names as returned by /context/nisar (e.g. both sides of a comparable pair).
    product_ids: list[str] = Field(min_length=1, max_length=4)
    # Default: every backscatter band of the product (HH and HV for most scenes).
    polarizations: list[str] | None = None
    # Average NxN pixels: 4 turns the 10 m product into a 40 m raster. Use the
    # same value for both dates of a pair.
    multilook: int = Field(default=4, ge=1, le=32)
    force: bool = False


class IngestTaskOut(BaseModel):
    id: str
    product_id: str | None = None
    location_id: str | None = None
    status: str  # QUEUED | RUNNING | COMPLETED | FAILED
    stage: str | None = None  # QUEUED | DOWNLOADING | CONVERTING | UPLOADING | READY
    progress: int = 0  # 0-100
    # Download progress in bytes; the client formats "2.31 of 6.85 GB" in its language.
    bytes_done: int | None = None
    bytes_total: int | None = None
    # When COMPLETED: observation_id, scene_id, asset_id, storage_path, bands...
    result: dict[str, Any] | None = None
    error: str | None = None
    enqueued_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
