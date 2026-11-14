from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.observation import Observation


class ObservationRepository:
    def list(
        self,
        db: Session,
        *,
        scene_id=None,
        location_id=None,
        storage_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Observation]:
        stmt = select(Observation)
        if scene_id:
            stmt = stmt.where(Observation.scene_id == scene_id)
        if location_id:
            stmt = stmt.where(Observation.location_id == location_id)
        if storage_status:
            stmt = stmt.where(Observation.storage_status == storage_status.upper())
        stmt = stmt.order_by(Observation.acquisition_date.desc()).limit(limit).offset(offset)
        return db.execute(stmt).scalars().all()

    def get(self, db: Session, observation_id) -> Observation | None:
        return db.get(Observation, observation_id)

    def create(
        self,
        db: Session,
        *,
        scene_id,
        location_id,
        acquisition_date: datetime,
        processing_version: str | None = None,
        storage_status: str = "DISCOVERED",
    ) -> Observation:
        observation = Observation(
            scene_id=scene_id,
            location_id=location_id,
            acquisition_date=acquisition_date,
            processing_version=processing_version,
            storage_status=storage_status,
        )
        db.add(observation)
        db.commit()
        db.refresh(observation)
        return observation

    def count(self, db: Session) -> int:
        return db.execute(select(func.count()).select_from(Observation)).scalar_one()
