"""Import every model so SQLAlchemy can resolve string-based FKs and Alembic sees them."""

from app.models.auxiliary_event import AuxiliaryEvent
from app.models.change_event import ChangeEvent
from app.models.change_metric import ChangeMetric
from app.models.evidence_record import EvidenceRecord
from app.models.location import Location
from app.models.nisar_scene import NisarScene
from app.models.observation import Observation
from app.models.processing_job import ProcessingJob
from app.models.raster_asset import RasterAsset

__all__ = [
    "AuxiliaryEvent",
    "ChangeEvent",
    "ChangeMetric",
    "EvidenceRecord",
    "Location",
    "NisarScene",
    "Observation",
    "ProcessingJob",
    "RasterAsset",
]
