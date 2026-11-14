"""Precipitation from NASA POWER (MERRA-2 / IMERG-corrected `PRECTOTCORR`), no API key.

POWER answers for a point but its precipitation grid is 0.5 x 0.625 degrees, so
one request describes the whole cell the point falls in. A window becomes ONE
auxiliary event: the rain accumulated over it, compared with what the monthly
climatology expects for those days.

(`gpm_client.py` stays a stub: reading IMERG granules needs Earthdata and a
gridded reader; POWER gives the same quantity as a ready-made daily series.)
"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

DAILY_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
CLIMATOLOGY_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/climatology/point"
PARAMETER = "PRECTOTCORR"
CELL_LAT, CELL_LON = 0.5, 0.625
_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def cell_bounds(longitude: float, latitude: float) -> tuple[float, float, float, float]:
    """Grid cell (west, south, east, north) that contains the point."""
    west = (longitude // CELL_LON) * CELL_LON
    south = (latitude // CELL_LAT) * CELL_LAT
    return west, south, west + CELL_LON, south + CELL_LAT


def _series(payload: dict[str, Any]) -> dict[str, float | None]:
    values = ((payload.get("properties") or {}).get("parameter") or {}).get(PARAMETER) or {}
    fill = (payload.get("header") or {}).get("fill_value", -999.0)
    return {key: (None if value == fill else float(value)) for key, value in values.items()}


def summarise(
    daily: dict[str, float | None],
    climatology: dict[str, float | None],
    start: date,
    end: date,
) -> dict[str, Any] | None:
    """Accumulated rain over [start, end] and its anomaly. None when POWER has no data yet."""
    days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    observed = [(day, daily.get(day.strftime("%Y%m%d"))) for day in days]
    known = [(day, value) for day, value in observed if value is not None]
    if not known:
        return None
    total = sum(value for _, value in known)
    peak_day, peak = max(known, key=lambda item: item[1])

    expected: float | None = 0.0
    for day, _ in known:  # mm/day for that month
        mean = climatology.get(_MONTHS[day.month - 1])
        if mean is None:
            expected = None
            break
        expected += mean
    anomaly_pct = None
    if expected is not None:
        # In the dry season the expectation approaches 0; the 1 mm floor avoids
        # infinite percentages without inventing precision.
        anomaly_pct = round(100.0 * (total - expected) / max(expected, 1.0), 1)
    return {
        "total_mm": round(total, 2),
        "expected_mm": None if expected is None else round(expected, 2),
        "anomaly_pct": anomaly_pct,
        "max_daily_mm": round(peak, 2),
        "peak_date": peak_day.isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "days_with_data": len(known),
        "days_requested": len(days),
        "daily_mm": {day.isoformat(): value for day, value in observed},
    }


class PowerClient:
    def fetch_event(
        self,
        *,
        longitude: float,
        latitude: float,
        start: datetime,
        end: datetime,
        timeout: float = 60.0,
    ) -> dict[str, Any] | None:
        """One PRECIPITATION event for the cell containing the point, or None without data."""
        first, last = start.date(), end.date()
        common = {
            "parameters": PARAMETER,
            "community": "RE",
            "longitude": round(longitude, 4),
            "latitude": round(latitude, 4),
            "format": "JSON",
        }
        with httpx.Client(timeout=timeout) as client:
            daily = client.get(
                DAILY_ENDPOINT,
                params={**common, "start": first.strftime("%Y%m%d"), "end": last.strftime("%Y%m%d")},
            )
            daily.raise_for_status()
            climatology = client.get(CLIMATOLOGY_ENDPOINT, params=common)
            climatology.raise_for_status()

        summary = summarise(_series(daily.json()), _series(climatology.json()), first, last)
        if summary is None:
            logger.info("POWER has no precipitation yet for %s..%s", first, last)
            return None
        west, south, east, north = cell_bounds(longitude, latitude)
        peak = date.fromisoformat(summary["peak_date"])
        return {
            "source": "POWER",
            "external_id": f"PRECTOTCORR:{west:.3f},{south:.3f}:{first:%Y%m%d}-{last:%Y%m%d}",
            "event_type": "PRECIPITATION",
            # The wettest day stands for the window on a timeline.
            "event_date": datetime.combine(peak, time(12), tzinfo=UTC),
            "bbox": (west, south, east, north),
            "magnitude": summary["total_mm"],  # mm accumulated over the window
            "metadata": {"units": "mm", "grid": "0.5 x 0.625 deg", **summary},
        }
