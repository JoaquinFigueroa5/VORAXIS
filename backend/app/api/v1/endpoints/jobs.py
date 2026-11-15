import uuid
from typing import Any

from fastapi import APIRouter

from app.dependencies import DbSession, Limit, Offset
from app.schemas.job import JobOut
from app.services.insights_service import InsightsService
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])
service = JobService()
insights = InsightsService()


@router.get("", response_model=list[JobOut])
def list_jobs(
    db: DbSession,
    status: str | None = None,
    location_id: uuid.UUID | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    return service.list(
        db, status=status, location_id=location_id, limit=limit, offset=offset
    )


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, db: DbSession) -> JobOut:
    return service.get(db, job_id)


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: uuid.UUID, db: DbSession) -> JobOut:
    return service.cancel(db, job_id)


@router.get("/{job_id}/insights")
def get_job_insights(job_id: uuid.UUID, db: DbSession) -> dict[str, Any]:
    """Aggregates for charts: by change type and direction, histograms, evidence and rain."""
    return insights.for_job(db, job_id)
