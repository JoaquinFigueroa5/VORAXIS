"""Analysis orchestration.

The endpoint validates the pair, creates a `processing_jobs` row and enqueues the
work in Redis. It never waits for raster processing.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AppError,
    IncompatibleObservationsError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.models.location import Location
from app.models.nisar_scene import NisarScene
from app.models.observation import Observation
from app.repositories.job_repository import JobRepository
from app.schemas.analysis import AnalysisAccepted, AnalysisRequest
from app.workers.queues import enqueue_analysis

logger = get_logger(__name__)


def compatibility_problems(
    db: Session, before: Observation, after: Observation, location: Location
) -> list[str]:
    """Rules 1 and 2 from docs/architecture.md, in executable form."""
    problems: list[str] = []

    if before.id == after.id:
        problems.append("before and after observations must be different")
    if before.acquisition_date >= after.acquisition_date:
        problems.append("before observation must predate the after observation")

    before_scene = db.get(NisarScene, before.scene_id)
    after_scene = db.get(NisarScene, after.scene_id)
    if before_scene is None or after_scene is None:
        raise NotFoundError("observation is missing its NISAR scene")

    if before_scene.product_type != after_scene.product_type:
        problems.append(
            f"product types differ ({before_scene.product_type} vs {after_scene.product_type})"
        )
    if (before_scene.maturity or "") != (after_scene.maturity or ""):
        problems.append("product maturity differs")

    pols_before = set(before_scene.polarization or [])
    pols_after = set(after_scene.polarization or [])
    if pols_before and pols_after and not pols_before & pols_after:
        problems.append("observations share no common polarisation")

    for scene in (before_scene, after_scene):
        overlaps = db.execute(
            select(func.ST_Intersects(NisarScene.footprint, Location.geometry)).where(
                NisarScene.id == scene.id, Location.id == location.id
            )
        ).scalar_one_or_none()
        if not overlaps:
            problems.append(f"scene {scene.product_id} does not overlap the requested AOI")

    return problems


def compatibility_warnings(before: Observation, after: Observation) -> list[str]:
    """Things worth telling the user that do not make the pair unusable."""
    warnings: list[str] = []
    if (
        before.processing_version
        and after.processing_version
        and before.processing_version != after.processing_version
    ):
        warnings.append(
            f"The two dates were processed with different software versions "
            f"({before.processing_version} vs {after.processing_version}); a small "
            "scene-wide offset between them is possible and is removed as the baseline."
        )
    return warnings


class AnalysisService:
    def __init__(self, jobs: JobRepository | None = None) -> None:
        self.jobs = jobs or JobRepository()

    def create(self, db: Session, request: AnalysisRequest) -> AnalysisAccepted:
        location = db.get(Location, request.location_id)
        if location is None:
            raise NotFoundError(f"location {request.location_id} not found")

        before = db.get(Observation, request.before_observation_id)
        after = db.get(Observation, request.after_observation_id)
        if before is None:
            raise NotFoundError(f"observation {request.before_observation_id} not found")
        if after is None:
            raise NotFoundError(f"observation {request.after_observation_id} not found")

        problems = compatibility_problems(db, before, after, location)
        if problems:
            raise IncompatibleObservationsError("; ".join(problems))

        job = self.jobs.create(
            db,
            location_id=location.id,
            before_observation_id=before.id,
            after_observation_id=after.id,
            parameters=request.parameters.model_dump(),
        )
        warnings = compatibility_warnings(before, after)
        if warnings:
            job.result = {"warnings": warnings}
            db.commit()

        try:
            enqueue_analysis(str(job.id), parameters=request.parameters.model_dump())
        except Exception as exc:  # Redis down: fail the job now, not silently later
            logger.exception("could not enqueue job %s", job.id)
            self.jobs.set_status(
                db, job, status="FAILED", error_message=f"queue unavailable: {exc}"
            )
            raise AppError("analysis queue is unavailable") from exc

        return AnalysisAccepted(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            message="Analysis queued successfully",
            warnings=warnings,
        )
