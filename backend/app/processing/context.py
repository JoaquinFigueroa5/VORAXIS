from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from rasterio.crs import CRS
from rasterio.transform import Affine


@dataclass
class LoadedRaster:
    """One band of a source raster, plus the grid it lives on."""

    path: Path
    array: np.ndarray
    invalid: np.ndarray
    transform: Affine
    crs: CRS
    profile: dict[str, Any]


@dataclass
class JobContext:
    """Everything the pipeline steps need. Mutable on purpose: steps fill it in."""

    job_id: UUID
    location_id: UUID
    before_observation_id: UUID
    after_observation_id: UUID
    parameters: dict[str, Any]
    workdir: Path

    product_type: str | None = None
    before: LoadedRaster | None = None
    after: LoadedRaster | None = None
    difference: np.ndarray | None = None
    change_mask: np.ndarray | None = None
    changed_fraction: float | None = None
    change_score: float | None = None
    valid_pixel_percentage: float | None = None
    change_event_ids: list[UUID] = field(default_factory=list)

    @property
    def polarization(self) -> str:
        return str(self.parameters.get("polarization", "VV"))

    @property
    def threshold_sigma(self) -> float:
        return float(self.parameters.get("change_threshold_sigma", 2.0))

    @property
    def minimum_valid_pixel_percentage(self) -> float:
        return float(self.parameters.get("minimum_valid_pixel_percentage", 80.0))
