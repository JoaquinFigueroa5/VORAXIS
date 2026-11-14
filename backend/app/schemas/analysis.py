import uuid
from typing import Literal

from pydantic import BaseModel, Field


class AnalysisParameters(BaseModel):
    polarization: str = "VV"
    minimum_valid_pixel_percentage: float = Field(default=80.0, ge=0, le=100)
    change_threshold_sigma: float = Field(default=2.0, gt=0, le=10)


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
