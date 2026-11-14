from app.core.exceptions import NotFoundError
from app.repositories.observation_repository import ObservationRepository
from app.schemas.observation import ObservationOut


class ObservationService:
    def __init__(self, repo: ObservationRepository | None = None) -> None:
        self.repo = repo or ObservationRepository()

    def list(self, db, **filters) -> list[ObservationOut]:
        return [ObservationOut.model_validate(o) for o in self.repo.list(db, **filters)]

    def get(self, db, observation_id) -> ObservationOut:
        observation = self.repo.get(db, observation_id)
        if observation is None:
            raise NotFoundError(f"observation {observation_id} not found")
        return ObservationOut.model_validate(observation)

    def prepare(self, db, *, scene_id, location_id, acquisition_date, processing_version=None):
        """Register an acquisition as ready for analysis."""
        return self.repo.create(
            db,
            scene_id=scene_id,
            location_id=location_id,
            acquisition_date=acquisition_date,
            processing_version=processing_version,
        )
