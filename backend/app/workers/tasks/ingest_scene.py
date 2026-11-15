from typing import Any

from rq import get_current_job

from app.core.database import SessionLocal
from app.services.ingest_service import IngestService

# Share of the progress bar each stage ends at; the download dominates.
_STAGE_END = {"DOWNLOADING": 80, "CONVERTING": 92, "UPLOADING": 98, "READY": 100}


def _reporter():
    """Write stage/progress into the RQ job so GET /ingest/{id} can show it."""
    job = get_current_job()

    def report(stage: str, detail: dict[str, Any] | None = None) -> None:
        if job is None:  # called outside a worker (tests, scripts)
            return
        detail = detail or {}
        progress = _STAGE_END.get(stage, 0)
        text = None
        if stage == "DOWNLOADING":
            done, total = detail.get("bytes", 0), detail.get("total")
            progress = int(_STAGE_END[stage] * done / total) if total else 0
            text = f"{done / 1e9:.2f} GB" + (f" de {total / 1e9:.2f} GB" if total else "")
        elif stage == "CONVERTING":
            progress = _STAGE_END["DOWNLOADING"] + 1
        elif stage == "UPLOADING":
            progress = _STAGE_END["CONVERTING"] + 1
        job.meta.update(stage=stage, progress=progress, detail=text)
        job.save_meta()

    return report


def run(
    location_id: str,
    scene_id: str | None = None,
    product_id: str | None = None,
    h5_path: str | None = None,
    polarizations: list[str] | None = None,
    frequency: str = "A",
    multilook: int = 1,
    force: bool = False,
) -> dict:
    """RQ task: HDF5 -> COG -> object storage -> Observation(READY) + RasterAsset(SOURCE).

    `h5_path` must be readable by the worker (e.g. under backend/data/, which is
    mounted at /app/data). Exceptions propagate so RQ keeps the traceback.
    """
    with SessionLocal() as db:
        result = IngestService().ingest(
            db,
            location_id=location_id,
            scene_id=scene_id,
            product_id=product_id,
            h5_path=h5_path,
            polarizations=polarizations,
            frequency=frequency,
            multilook=multilook,
            force=force,
            on_progress=_reporter(),
        )
    return result.as_dict()
