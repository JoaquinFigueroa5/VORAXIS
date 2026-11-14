"""Tile cache warm-up.

Tiles are rendered on demand from the COGs (`services/tile_service.py`); this
task only pre-downloads a job's rasters so the first map request is fast.
"""

from app.core.database import SessionLocal
from app.services.tile_service import LAYERS, TileService


def run(job_id: str) -> list[str]:
    service = TileService()
    warmed = []
    with SessionLocal() as db:
        description = service.describe(db, job_id, "")
        job = service._job(db, job_id)
        for layer in LAYERS:
            if layer in description["layers"]:
                service._local(service._asset(db, job, layer))
                warmed.append(layer)
    return warmed
