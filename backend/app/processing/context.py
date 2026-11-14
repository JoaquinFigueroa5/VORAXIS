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
    units: str = "linear"  # "dB" for ingested GCOV sources
    band: int = 1
    polarization: str | None = None


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
    difference: np.ndarray | None = None  # signed log-ratio in dB, NaN where invalid
    change_mask: np.ndarray | None = None
    changed_fraction: float | None = None
    threshold_db: float | None = None
    baseline_db: float | None = None
    change_score: float | None = None  # strongest per-polygon score of the job
    valid_pixel_percentage: float | None = None
    change_event_ids: list[UUID] = field(default_factory=list)
    change_features: dict[UUID, Any] = field(default_factory=dict)  # id -> vectorization.Region
    evidence_sources: dict[str, Any] = field(default_factory=dict)
    change_types: dict[str, int] = field(default_factory=dict)

    @property
    def polarization(self) -> str:
        return str(self.parameters.get("polarization") or "HH").upper()

    @property
    def threshold_sigma(self) -> float:
        return float(self.parameters.get("change_threshold_sigma", 2.0))

    @property
    def minimum_valid_pixel_percentage(self) -> float:
        return float(self.parameters.get("minimum_valid_pixel_percentage", 80.0))

    @property
    def smoothing_window(self) -> int:
        return int(self.parameters.get("smoothing_window", 5))

    @property
    def noise_floor_db(self) -> float | None:
        value = self.parameters.get("noise_floor_db", -30.0)
        return None if value is None else float(value)

    @property
    def edge_buffer_pixels(self) -> int:
        return int(self.parameters.get("edge_buffer_pixels", 16))

    @property
    def minimum_area_m2(self) -> float:
        return float(self.parameters.get("minimum_area_km2", 0.01)) * 1e6
