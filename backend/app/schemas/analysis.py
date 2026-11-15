import uuid
from typing import Literal

from pydantic import BaseModel, Field


class AnalysisParameters(BaseModel):
    # NISAR L-band is HH/HV over most land; the source COG must contain the band.
    polarization: str = "HH"
    minimum_valid_pixel_percentage: float = Field(default=80.0, ge=0, le=100)
    change_threshold_sigma: float = Field(default=2.0, gt=0, le=10)
    # Boxcar window (pixels) applied to the log-ratio to tame speckle; 1 disables it.
    smoothing_window: int = Field(default=5, ge=1, le=31)
    # Pixels darker than this on both dates (calm water, shadow) are ignored; null disables.
    noise_floor_db: float | None = Field(default=-30.0, ge=-60, le=0)
    # Pixels this close to missing data (swath rim) are ignored; 0 disables.
    edge_buffer_pixels: int = Field(default=16, ge=0, le=200)
    # Changed areas smaller than this are dropped.
    minimum_area_km2: float = Field(default=0.01, ge=0, le=100)
    # Query USGS / FIRMS / POWER for the interval between the two acquisitions.
    fetch_auxiliary: bool = True


class AnalysisRequest(BaseModel):
    location_id: uuid.UUID
    before_observation_id: uuid.UUID
    after_observation_id: uuid.UUID
    analysis_type: Literal["GCOV_CHANGE"] = "GCOV_CHANGE"
    parameters: AnalysisParameters = Field(default_factory=AnalysisParameters)


class AnalysisAccepted(BaseModel):
    job_id: uuid.UUID
    status: str
    progress: int
    message: str
    # The pair is usable, but the user should know (e.g. different processing versions).
    warnings: list[str] = Field(default_factory=list)
