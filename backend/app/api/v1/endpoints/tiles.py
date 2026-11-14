"""Raster tiles for the map: before / after / difference / mask of an analysis job.

    GET /jobs/{job_id}/tiles                      layer URLs, bounds, zoom range, legend
    GET /jobs/{job_id}/tiles/{z}/{x}/{y}?layer=   256 px PNG (XYZ, Web Mercator)

The same two routes exist under /changes/{change_id}; they resolve to the
change's job.
"""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Response

from app.core.config import settings
from app.dependencies import DbSession
from app.services.change_service import ChangeService
from app.services.tile_service import TileService

router = APIRouter(tags=["tiles"])
tiles = TileService()
changes = ChangeService()

Layer = Annotated[
    Literal["before", "after", "difference", "mask"],
    Query(description="Which raster to draw"),
]
Polarization = Annotated[
    str | None,
    Query(description="before/after only; defaults to the polarisation the job analysed"),
]
# Rasters of a finished job never change; a re-run registers new assets.
_HEADERS = {"Cache-Control": "public, max-age=3600"}


def _png(content: bytes) -> Response:
    return Response(content=content, media_type="image/png", headers=_HEADERS)


@router.get("/jobs/{job_id}/tiles")
def describe_job_tiles(job_id: uuid.UUID, db: DbSession) -> dict[str, Any]:
    return tiles.describe(db, job_id, f"{settings.api_prefix}/jobs/{job_id}/tiles")


@router.get("/jobs/{job_id}/tiles/{z}/{x}/{y}", response_class=Response)
def get_job_tile(
    job_id: uuid.UUID,
    z: int,
    x: int,
    y: int,
    db: DbSession,
    layer: Layer = "difference",
    polarization: Polarization = None,
) -> Response:
    return _png(tiles.tile(db, job_id, layer, z, x, y, polarization))


@router.get("/changes/{change_id}/tiles")
def describe_change_tiles(change_id: uuid.UUID, db: DbSession) -> dict[str, Any]:
    change = changes.get(db, change_id)
    return tiles.describe(db, change.job_id, f"{settings.api_prefix}/changes/{change_id}/tiles")


@router.get("/changes/{change_id}/tiles/{z}/{x}/{y}", response_class=Response)
def get_change_tile(
    change_id: uuid.UUID,
    z: int,
    x: int,
    y: int,
    db: DbSession,
    layer: Layer = "difference",
    polarization: Polarization = None,
) -> Response:
    change = changes.get(db, change_id)
    return _png(tiles.tile(db, change.job_id, layer, z, x, y, polarization))
