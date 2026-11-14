from app.processing.pipeline import run as run_pipeline


def run(job_id: str, parameters: dict | None = None) -> None:
    """RQ task. Exceptions propagate so RQ marks the job failed and keeps the traceback."""
    run_pipeline(job_id, parameters or {})
