from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.processing_job import ProcessingJob


class JobRepository:
    def get(self, db: Session, job_id) -> ProcessingJob | None:
        return db.get(ProcessingJob, job_id)

    def list(
        self,
        db: Session,
        *,
        status: str | None = None,
        location_id=None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[ProcessingJob]:
        stmt = select(ProcessingJob)
        if status:
            stmt = stmt.where(ProcessingJob.status == status.upper())
        if location_id:
            stmt = stmt.where(ProcessingJob.location_id == location_id)
        stmt = stmt.order_by(ProcessingJob.created_at.desc()).limit(limit).offset(offset)
        return db.execute(stmt).scalars().all()

    def create(
        self,
        db: Session,
        *,
        location_id,
        before_observation_id,
        after_observation_id,
        parameters: dict | None = None,
    ) -> ProcessingJob:
        job = ProcessingJob(
            location_id=location_id,
            before_observation_id=before_observation_id,
            after_observation_id=after_observation_id,
            status="PENDING",
            progress=0,
            parameters=parameters,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def set_status(
        self,
        db: Session,
        job: ProcessingJob,
        *,
        status: str,
        progress: int | None = None,
        current_step: str | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> ProcessingJob:
        job.status = status
        if progress is not None:
            job.progress = progress
        if current_step is not None:
            job.current_step = current_step
        if error_message is not None:
            job.error_message = error_message
        if started_at is not None:
            job.started_at = started_at
        if finished_at is not None:
            job.finished_at = finished_at
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def count_by_status(self, db: Session) -> dict[str, int]:
        rows = db.execute(
            select(ProcessingJob.status, func.count()).group_by(ProcessingJob.status)
        ).all()
        return {status: total for status, total in rows}
