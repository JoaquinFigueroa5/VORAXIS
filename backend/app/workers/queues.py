"""RQ wiring. The queue is the only thing the web process knows about the worker."""

from functools import lru_cache

from redis import Redis
from rq import Queue

from app.core.config import settings

ANALYSIS_TASK = "app.workers.tasks.analyze_job.run"
INGEST_TASK = "app.workers.tasks.ingest_scene.run"


@lru_cache
def get_connection() -> Redis:
    return Redis.from_url(settings.redis_url)


@lru_cache
def get_queue() -> Queue:
    return Queue(settings.redis_queue, connection=get_connection())


def enqueue_analysis(job_id: str, parameters: dict | None = None) -> str:
    """Enqueue by import path so the API does not need the processing code loaded."""
    rq_job = get_queue().enqueue(
        ANALYSIS_TASK,
        job_id,
        parameters=parameters or {},
        job_timeout=3600,
        result_ttl=86400,
        failure_ttl=86400,
    )
    return rq_job.id


def enqueue_ingest(location_id: str, **options) -> str:
    """Queue an HDF5 -> COG ingestion. `options` are `ingest_scene.run` keyword arguments."""
    rq_job = get_queue().enqueue(
        INGEST_TASK,
        location_id,
        **options,
        job_timeout=4 * 3600,  # multi-GB download + conversion
        result_ttl=86400,
        failure_ttl=86400,
    )
    return rq_job.id
