from app.core.database import SessionLocal
from app.services.ingest_service import IngestService


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
        )
    return result.as_dict()
