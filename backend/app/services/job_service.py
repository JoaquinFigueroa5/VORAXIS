from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobOut


class JobService:
    def __init__(self, repo: JobRepository | None = None) -> None:
        self.repo = repo or JobRepository()

    def list(self, db, status: str | None = None, limit: int = 50, offset: int = 0) -> list[JobOut]:
        return [
            JobOut.model_validate(job)
            for job in self.repo.list(db, status=status, limit=limit, offset=offset)
        ]

    def get(self, db, job_id) -> JobOut:
        job = self.repo.get(db, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        return JobOut.model_validate(job)

    def cancel(self, db, job_id) -> JobOut:
        job = self.repo.get(db, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        if job.status not in ("PENDING", "RUNNING"):
            raise ConflictError(f"job is {job.status} and cannot be cancelled")
        # The worker re-reads the row between pipeline steps and stops there.
        self.repo.set_status(db, job, status="CANCELLED", error_message="cancelled by user")
        return JobOut.model_validate(job)
