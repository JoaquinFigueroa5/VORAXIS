"""RQ wiring. The queue is the only thing the web process knows about the worker."""

from functools import lru_cache

from redis import Redis
from rq import Queue

from app.core.config import settings

ANALYSIS_TASK = "app.workers.tasks.analyze_job.run"


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
