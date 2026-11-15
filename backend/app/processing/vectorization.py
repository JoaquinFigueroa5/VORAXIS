"""Polygonise the change mask, reproject to WGS84 and persist change events.

Every connected region of the mask becomes one change event with its *own*
statistics: score, mean change, direction and backscatter before/after.
"""

from dataclasses import dataclass

import numpy as np
import rasterio.features
from pyproj import Geod
from rasterio.warp import transform_geom
from scipy import ndimage
from shapely.geometry import MultiPolygon, shape
from sqlalchemy import func

from app.core.exceptions import ProcessingError
from app.core.logging import get_logger
from app.models.change_event import ChangeEvent
from app.processing import metrics
from app.processing.algorithms import gcov
from app.processing.quality_control import require_pair_loaded

logger = get_logger(__name__)

GEOD = Geod(ellps="WGS84")


@dataclass
class Region:
    """One connected changed area and what happened inside it."""

    geometry: MultiPolygon  # EPSG:4326
    area_km2: float
    pixel_count: int
    mean_change_db: float  # signed, relative to the scene baseline
    peak_change_db: float  # signed value of the strongest pixel
    mean_before_db: float
    mean_after_db: float
    score: float

    @property
    def direction(self) -> str:
        return "DECREASE" if self.mean_change_db < 0 else "INCREASE"


def _area_m2(geometry_wgs84) -> float:
    area, _ = GEOD.geometry_area_perimeter(geometry_wgs84)
    return abs(area)


def extract_regions(context) -> list[Region]:
    before, after = require_pair_loaded(context)
    if context.change_mask is None or context.difference is None:
        raise ProcessingError("change detection produced no mask")

    labels, count = ndimage.label(context.change_mask)  # 4-connectivity, like `shapes`
    if count == 0:
        return []
    index = np.arange(1, count + 1)
    baseline = context.baseline_db or 0.0
    threshold = context.threshold_db or gcov.MINIMUM_THRESHOLD_DB
    deviation = np.nan_to_num(context.difference - baseline, nan=0.0)
    before_db = np.nan_to_num(gcov.to_db(before.array, before.units), nan=0.0)
    after_db = np.nan_to_num(gcov.to_db(after.array, after.units), nan=0.0)

    pixels = ndimage.sum(context.change_mask, labels, index)
    mean_change = ndimage.mean(deviation, labels, index)
    mean_abs = ndimage.mean(np.abs(deviation), labels, index)
    low = ndimage.minimum(deviation, labels, index)
    high = ndimage.maximum(deviation, labels, index)
    mean_before = ndimage.mean(before_db, labels, index)
    mean_after = ndimage.mean(after_db, labels, index)

    geometries: dict[int, list] = {}
    shapes = rasterio.features.shapes(
        labels.astype("int32"), mask=labels > 0, transform=before.transform
    )
    for geometry, value in shapes:
        wgs84 = shape(transform_geom(before.crs, "EPSG:4326", geometry))
        if not wgs84.is_valid:
            wgs84 = wgs84.buffer(0)
        if not wgs84.is_empty:
            geometries.setdefault(int(value), []).append(wgs84)

    regions = []
    for label, parts in geometries.items():
        polygons = [
            polygon
            for part in parts
            for polygon in (part.geoms if part.geom_type == "MultiPolygon" else [part])
            if polygon.geom_type == "Polygon"
        ]
        if not polygons:
            continue
        geometry = MultiPolygon(polygons)
        area = _area_m2(geometry)
        if area < context.minimum_area_m2:
            continue
        i = label - 1
        peak = low[i] if abs(low[i]) >= abs(high[i]) else high[i]
        regions.append(
            Region(
                geometry=geometry,
                area_km2=round(area / 1e6, 6),
                pixel_count=int(pixels[i]),
                mean_change_db=float(mean_change[i]),
                peak_change_db=float(peak),
                mean_before_db=float(mean_before[i]),
                mean_after_db=float(mean_after[i]),
                score=gcov.score(float(mean_abs[i]), threshold),
            )
        )
    regions.sort(key=lambda region: region.score, reverse=True)
    return regions


def mask_to_polygons(context) -> list[MultiPolygon]:
    return [region.geometry for region in extract_regions(context)]


def run(db, context) -> None:
    regions = extract_regions(context)
    if not regions:
        logger.info("job %s produced no change events above the minimum area", context.job_id)
        db.commit()
        return

    for region in regions:
        event = ChangeEvent(
            job_id=context.job_id,
            change_type="UNCLASSIFIED",
            geometry=func.ST_GeomFromText(region.geometry.wkt, 4326),
            area_km2=region.area_km2,
            change_score=round(region.score, 4),
            valid_pixel_percentage=context.valid_pixel_percentage,
            direction=region.direction,
            mean_change_db=round(region.mean_change_db, 4),
        )
        db.add(event)
        db.flush()
        context.change_event_ids.append(event.id)
        context.change_features[event.id] = region
        metrics.record(db, context, event, region)

    context.change_score = max(region.score for region in regions)
    db.commit()
    logger.info("job %s created %s change events", context.job_id, len(regions))
