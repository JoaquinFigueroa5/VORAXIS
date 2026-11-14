from sqlalchemy import func, select

from app.models.location import Location
from app.repositories.change_repository import ChangeRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.job_repository import JobRepository
from app.repositories.nisar_repository import NisarRepository
from app.repositories.observation_repository import ObservationRepository
from app.schemas.common import InsightsOut


class InsightsService:
    def summary(self, db) -> InsightsOut:
        return InsightsOut(
            locations=db.execute(select(func.count()).select_from(Location)).scalar_one(),
            scenes=NisarRepository().count(db),
            observations=ObservationRepository().count(db),
            jobs=JobRepository().count_by_status(db),
            change_events=ChangeRepository().count(db),
            change_area_km2=round(ChangeRepository().total_area_km2(db), 3),
            evidence_records=EvidenceRepository().count(db),
            auxiliary_events=EvidenceRepository().count_auxiliary(db),
        )
