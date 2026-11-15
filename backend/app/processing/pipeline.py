"""Pipeline orchestration.

Each step receives the shared context and must be idempotent enough to be re-run
for the same job (the difference rasters are rewritten, change events for the job
are replaced before vectorising).
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.core.logging import get_logger
from app.core.storage import ensure_bucket
from app.models.processing_job import ProcessingJob
from app.models.nisar_scene import NisarScene
from app.processing import (
    alignment,
    change_detection,
    download,
    preprocessing,
    raster_export,
    vectorization,
)
from app.processing.context import JobContext
from app.repositories.change_repository import ChangeRepository
from app.repositories.job_repository import JobRepository
from app.repositories.location_repository import LocationRepository
from app.repositories.observation_repository import ObservationRepository
from app.evidence import engine as evidence_engine

logger = get_logger(__name__)

STEPS = (
    ("DOWNLOADING", 10, download.run),
    ("PREPROCESSING", 25, preprocessing.run),
    ("ALIGNMENT", 35, alignment.run),
    ("CHANGE_DETECTION", 50, change_detection.run),
    ("VECTORIZATION", 70, vectorization.run),
    ("EVIDENCE_ANALYSIS", 85, evidence_engine.run),
    ("EXPORTING", 95, raster_export.run),
)


def _update(db, jobs: JobRepository, job: ProcessingJob, **fields) -> None:
    jobs.set_status(db, job, **fields)


def run(job_id: str, parameters: dict | None = None) -> None:
    jobs = JobRepository()
    changes = ChangeRepository()

    # The API also does this on boot; the worker may start alone.
    try:
        ensure_bucket()
    except Exception as exc:
        logger.warning("object storage is not reachable yet: %s", exc)

    with _session() as db:
        job = db.get(ProcessingJob, UUID(job_id))
        if job is None:
            logger.warning("job %s no longer exists", job_id)
            return
        if job.status in ("CANCELLED", "COMPLETED"):
            return

        location = LocationRepository().get_model(db, job.location_id)
        before = ObservationRepository().get(db, job.before_observation_id)
        after = ObservationRepository().get(db, job.after_observation_id)
        if location is None or before is None or after is None:
            _update(db, jobs, job, status="FAILED", error_message="job references missing rows")
            return

        before_scene = db.get(NisarScene, before.scene_id)
        workdir = Path(tempfile.mkdtemp(prefix=f"job-{job_id}-"))
        context = JobContext(
            job_id=job.id,
            location_id=location.id,
            before_observation_id=before.id,
            after_observation_id=after.id,
            parameters=parameters or {},
            workdir=workdir,
            product_type=before_scene.product_type if before_scene else None,
        )

        _update(db, jobs, job, status="RUNNING", started_at=datetime.now(UTC), progress=0)
        changes.delete_for_job(db, job.id)
        db.commit()

        try:
            for step, progress, handler in STEPS:
                db.refresh(job)
                if job.status == "CANCELLED":
                    logger.info("job %s cancelled before %s", job_id, step)
                    return
                _update(db, jobs, job, status="RUNNING", progress=progress, current_step=step)
                logger.info("job %s step %s", job_id, step)
                handler(db, context)

            job.result = {
                **(job.result or {}),  # keeps the warnings recorded when it was queued
                "aoi_coverage_percentage": context.aoi_coverage_percentage,
                "polarization": context.polarization,
                "change_events": len(context.change_event_ids),
                "change_types": context.change_types,
                "threshold_db": context.threshold_db,
                "baseline_db": context.baseline_db,
                "changed_pixel_fraction": context.changed_fraction,
                "valid_pixel_percentage": context.valid_pixel_percentage,
                "evidence_sources": context.evidence_sources,
            }
            _update(
                db,
                jobs,
                job,
                status="COMPLETED",
                progress=100,
                current_step="DONE",
                finished_at=datetime.now(UTC),
            )
        except NotImplementedError as exc:
            logger.warning("job %s hit an unimplemented step: %s", job_id, exc)
            _update(
                db,
                jobs,
                job,
                status="FAILED",
                error_message=f"not implemented: {exc}",
                finished_at=datetime.now(UTC),
            )
            raise
        except Exception as exc:
            logger.exception("job %s failed", job_id)
            _update(
                db,
                jobs,
                job,
                status="FAILED",
                error_message=str(exc)[:2000],
                finished_at=datetime.now(UTC),
            )
            raise


def _session():
    from app.core.database import SessionLocal

    return SessionLocal()
