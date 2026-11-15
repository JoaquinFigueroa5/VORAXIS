"""Analysis orchestration.

The endpoint validates the pair, creates a `processing_jobs` row and enqueues the
work in Redis. It never waits for raster processing.
"""

from typing import Any

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
) -> list[dict[str, Any]]:
    """Rules 1 and 2 from docs/architecture.md, in executable form.

    Each problem is `{code, params}`; the client writes the sentence.
    """
    problems: list[dict[str, Any]] = []

    if before.id == after.id:
        problems.append({"code": "same_observation"})
    if before.acquisition_date >= after.acquisition_date:
        problems.append({"code": "dates_not_increasing"})

    before_scene = db.get(NisarScene, before.scene_id)
    after_scene = db.get(NisarScene, after.scene_id)
    if before_scene is None or after_scene is None:
        raise NotFoundError("observation is missing its NISAR scene", code="observation_without_scene")

    if before_scene.product_type != after_scene.product_type:
        problems.append(
            {
                "code": "product_type_differs",
                "params": {
                    "before": before_scene.product_type,
                    "after": after_scene.product_type,
                },
            }
        )
    if (before_scene.maturity or "") != (after_scene.maturity or ""):
        problems.append({"code": "maturity_differs"})

    pols_before = set(before_scene.polarization or [])
    pols_after = set(after_scene.polarization or [])
    if pols_before and pols_after and not pols_before & pols_after:
        problems.append({"code": "no_common_polarisation"})

    for scene in (before_scene, after_scene):
        overlaps = db.execute(
            select(func.ST_Intersects(NisarScene.footprint, Location.geometry)).where(
                NisarScene.id == scene.id, Location.id == location.id
            )
        ).scalar_one_or_none()
        if not overlaps:
            problems.append(
                {"code": "scene_without_overlap", "params": {"product_id": scene.product_id}}
            )

    return problems


def compatibility_warnings(before: Observation, after: Observation) -> list[dict[str, Any]]:
    """Things worth telling the user that do not make the pair unusable."""
    warnings: list[dict[str, Any]] = []
    if (
        before.processing_version
        and after.processing_version
        and before.processing_version != after.processing_version
    ):
        warnings.append(
            {
                "code": "processing_version_differs",
                "params": {
                    "before": before.processing_version,
                    "after": after.processing_version,
                },
            }
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
            raise IncompatibleObservationsError(
                "; ".join(problem["code"] for problem in problems),
                params={"problems": problems},
            )

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
                db, job, status="FAILED", error_message="queue_unavailable"
            )
            raise AppError("analysis queue is unavailable", code="queue_unavailable") from exc

        return AnalysisAccepted(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            warnings=warnings,
        )
