"""Ingestion requested through the API: queue it, then report how far it got.

Ingestions are RQ jobs (a multi-GB download does not belong in a request). The
task records its stage and progress in the RQ job's `meta`, which is what the
status endpoint reads. They share the worker with analyses, so they run one at
a time, in order.
"""

from pathlib import Path
from typing import Any

from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.integrations.nisar.earthdata_client import EarthdataClient
from app.integrations.nisar.product_name import parse_product_name
from app.models.location import Location
from app.schemas.ingest import IngestRequest, IngestTaskOut
from app.workers.queues import INGEST_TASK, enqueue_ingest, get_connection, get_queue

logger = get_logger(__name__)

_STATUS = {
    "queued": "QUEUED",
    "deferred": "QUEUED",
    "scheduled": "QUEUED",
    "started": "RUNNING",
    "finished": "COMPLETED",
    "failed": "FAILED",
    "stopped": "FAILED",
    "canceled": "FAILED",
}


def _last_line(text: str | None) -> str | None:
    """RQ keeps the whole traceback; the last line is the message a person can read."""
    if not text:
        return None
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[-1][:500] if lines else None


def to_out(job: Job) -> IngestTaskOut:
    meta = job.meta or {}
    raw = job.get_status(refresh=True)
    # RQ returns an enum; its `value` is the plain word ("finished", "started"...).
    status = _STATUS.get(str(getattr(raw, "value", raw)), "QUEUED")
    result = job.return_value() if status == "COMPLETED" else None
    progress = int(meta.get("progress", 0))
    stage = meta.get("stage", "QUEUED")
    if status == "COMPLETED":
        progress, stage = 100, "READY"
    return IngestTaskOut(
        id=job.id,
        product_id=meta.get("product_id"),
        location_id=meta.get("location_id"),
        status=status,
        stage=stage,
        progress=progress,
        detail=meta.get("detail"),
        result=result if isinstance(result, dict) else None,
        error=_last_line(job.exc_info) if status == "FAILED" else None,
        enqueued_at=job.enqueued_at,
        started_at=job.started_at,
        ended_at=job.ended_at,
    )


class IngestTaskService:
    def __init__(self, earthdata: EarthdataClient | None = None) -> None:
        self.earthdata = earthdata or EarthdataClient()

    def create(self, db, request: IngestRequest) -> list[IngestTaskOut]:
        location = db.get(Location, request.location_id)
        if location is None:
            raise NotFoundError(f"location {request.location_id} not found")

        product_ids = list(dict.fromkeys(pid.strip().removesuffix(".h5") for pid in request.product_ids))
        for product_id in product_ids:
            name = parse_product_name(product_id)
            if name is None:
                raise AppError(f"'{product_id}' is not a NISAR granule name")
            if name.product_type != "GCOV":
                raise AppError(
                    f"{product_id} is a {name.product_type} product; only GCOV can be ingested"
                )
            cached = Path(settings.nisar_data_dir) / f"{product_id}.h5"
            if not cached.is_file() and not self.earthdata.configured:
                raise AppError(
                    "downloads need Earthdata credentials: set EARTHDATA_USERNAME and "
                    "EARTHDATA_PASSWORD in .env"
                )

        tasks = []
        for product_id in product_ids:
            try:
                job_id = enqueue_ingest(
                    str(request.location_id),
                    product_id=product_id,
                    polarizations=request.polarizations,
                    multilook=request.multilook,
                    force=request.force,
                )
            except Exception as exc:
                logger.exception("could not enqueue ingestion of %s", product_id)
                raise AppError("ingestion queue is unavailable") from exc
            tasks.append(self.get(job_id))
        return tasks

    def get(self, task_id: str) -> IngestTaskOut:
        try:
            job = Job.fetch(task_id, connection=get_connection())
        except NoSuchJobError as exc:
            raise NotFoundError(
                f"ingestion {task_id} not found (finished tasks are kept for 24 h)"
            ) from exc
        if job.func_name != INGEST_TASK:
            raise NotFoundError(f"ingestion {task_id} not found")
        return to_out(job)

    def list(self, location_id: str | None = None, limit: int = 50) -> list[IngestTaskOut]:
        """Queued, running and recently finished ingestions, newest first."""
        queue = get_queue()
        ids: list[str] = list(queue.started_job_registry.get_job_ids())
        ids += list(queue.job_ids)
        ids += list(queue.finished_job_registry.get_job_ids())
        ids += list(queue.failed_job_registry.get_job_ids())
        tasks: list[IngestTaskOut] = []
        for job in Job.fetch_many(list(dict.fromkeys(ids)), connection=get_connection()):
            if job is None or job.func_name != INGEST_TASK:
                continue
            task = to_out(job)
            if location_id and task.location_id != str(location_id):
                continue
            tasks.append(task)
        tasks.sort(key=lambda task: task.enqueued_at.timestamp() if task.enqueued_at else 0, reverse=True)
        return tasks[:limit]

    @staticmethod
    def describe_queue() -> dict[str, Any]:
        queue = get_queue()
        return {"queued": queue.count, "running": queue.started_job_registry.count}
