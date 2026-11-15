"""Live context for any point: NISAR coverage, earthquakes, rain, fires and a timeline.

No ingested scene or stored location is needed. Use `days` for "the last N
days", or `start`/`end` (YYYY-MM-DD) for a window in the past.
"""

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.services.context_service import ContextService

router = APIRouter(prefix="/context", tags=["context"])
service = ContextService()

Latitude = Annotated[float, Query(ge=-90, le=90)]
Longitude = Annotated[float, Query(ge=-180, le=180)]
Start = Annotated[date | None, Query(description="YYYY-MM-DD; overrides `days`")]
End = Annotated[date | None, Query(description="YYYY-MM-DD; defaults to today")]


@router.get("/nisar")
def get_nisar(
    lat: Latitude,
    lon: Longitude,
    days: Annotated[int, Query(ge=1, le=730)] = 120,
    start: Start = None,
    end: End = None,
    level: Literal["ALL", "GCOV", "GUNW", "GSLC", "RSLC", "GOFF", "SME2"] = "ALL",
    max_results: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    """NISAR products over the point: freshness per level and ready-to-analyse GCOV pairs."""
    return service.nisar(
        latitude=lat,
        longitude=lon,
        days=days,
        start=start,
        end=end,
        level=level,
        max_results=max_results,
    )


@router.get("/earthquakes")
def get_earthquakes(
    lat: Latitude,
    lon: Longitude,
    radius_km: Annotated[float, Query(ge=10, le=1500)] = 250,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start: Start = None,
    end: End = None,
    min_magnitude: Annotated[float, Query(ge=0, le=9)] = 2.5,
) -> dict[str, Any]:
    """USGS earthquakes within the radius, each with its distance to the point."""
    return service.earthquakes(
        latitude=lat,
        longitude=lon,
        radius_km=radius_km,
        days=days,
        start=start,
        end=end,
        min_magnitude=min_magnitude,
    )


@router.get("/precipitation")
def get_precipitation(
    lat: Latitude,
    lon: Longitude,
    days: Annotated[int, Query(ge=5, le=365)] = 30,
    start: Start = None,
    end: End = None,
) -> dict[str, Any]:
    """NASA POWER daily rain, the total and its anomaly against the monthly climatology."""
    return service.precipitation(latitude=lat, longitude=lon, days=days, start=start, end=end)


@router.get("/fires")
def get_fires(
    lat: Latitude,
    lon: Longitude,
    radius_km: Annotated[float, Query(ge=1, le=500)] = 50,
    days: Annotated[int, Query(ge=1, le=31)] = 5,
    start: Start = None,
    end: End = None,
) -> dict[str, Any]:
    """NASA FIRMS active-fire detections within the radius (at most 31 days per request)."""
    return service.fires(
        latitude=lat, longitude=lon, radius_km=radius_km, days=days, start=start, end=end
    )


@router.get("/timeline")
def get_timeline(
    lat: Latitude,
    lon: Longitude,
    radius_km: Annotated[float, Query(ge=10, le=1500)] = 100,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start: Start = None,
    end: End = None,
    min_magnitude: Annotated[float, Query(ge=0, le=9)] = 2.5,
) -> dict[str, Any]:
    """NISAR acquisitions, earthquakes, heavy-rain days and fire days, newest first."""
    return service.timeline(
        latitude=lat,
        longitude=lon,
        radius_km=radius_km,
        days=days,
        start=start,
        end=end,
        min_magnitude=min_magnitude,
    )
