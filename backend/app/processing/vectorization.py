"""Polygonise the change mask, reproject to WGS84 and persist change events."""

import rasterio.features
from pyproj import Geod
from rasterio.warp import transform_geom
from shapely.geometry import MultiPolygon, shape
from sqlalchemy import func

from app.core.exceptions import ProcessingError
from app.core.logging import get_logger
from app.models.change_event import ChangeEvent
from app.processing import metrics
from app.processing.quality_control import require_pair_loaded
from app.repositories.change_repository import ChangeRepository

logger = get_logger(__name__)

GEOD = Geod(ellps="WGS84")
MIN_AREA_M2 = 1_000.0  # ignore slivers under ~0.001 km²


def _area_m2(geometry_wgs84) -> float:
    area, _ = GEOD.geometry_area_perimeter(geometry_wgs84)
    return abs(area)


def mask_to_polygons(context) -> list[MultiPolygon]:
    before, _ = require_pair_loaded(context)
    if context.change_mask is None:
        raise ProcessingError("change detection produced no mask")

    mask = context.change_mask.astype("uint8")
    shapes = rasterio.features.shapes(mask, transform=before.transform)
    polygons = []
    for geometry, value in shapes:
        if not value:
            continue
        wgs84 = shape(transform_geom(before.crs, "EPSG:4326", geometry))
        if not wgs84.is_valid:
            wgs84 = wgs84.buffer(0)
        if wgs84.is_empty or _area_m2(wgs84) < MIN_AREA_M2:
            continue
        polygons.append(wgs84)
    return [MultiPolygon([p]) if p.geom_type == "Polygon" else p for p in polygons]


def run(db, context) -> None:
    changes = ChangeRepository()
    polygons = mask_to_polygons(context)
    if not polygons:
        logger.info("job %s produced no change events above the minimum area", context.job_id)
        db.commit()
        return

    valid_percentage = context.valid_pixel_percentage
    for polygon in polygons:
        event = ChangeEvent(
            job_id=context.job_id,
            change_type="UNCLASSIFIED",
            geometry=func.ST_GeomFromText(polygon.wkt, 4326),
            area_km2=round(_area_m2(polygon) / 1e6, 6),
            change_score=context.change_score,
            valid_pixel_percentage=valid_percentage,
        )
        db.add(event)
        db.flush()
        context.change_event_ids.append(event.id)
        metrics.record(db, context, event)

    db.commit()
    logger.info("job %s created %s change events", context.job_id, len(polygons))
