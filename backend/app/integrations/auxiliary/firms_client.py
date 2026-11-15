"""NASA FIRMS active-fire detections (VIIRS, 375 m).

Area API:  /api/area/csv/{MAP_KEY}/{source}/{west,south,east,north}/{days}/{start-date}

A request covers at most `MAX_DAYS` days, so a longer window is walked in
chunks. The NRT collections hold roughly the last two months; older windows
need the standard-processing (`_SP`) collections, which are tried when NRT
returns nothing.

Suomi NPP stopped delivering data on 2026-11-02, so NOAA-20 and NOAA-21 are the
current satellites; S-NPP is still queried because it covers earlier dates. One
collection failing (retired, renamed) does not discard the others: the lookup
only fails when no collection answered at all.

A MAP_KEY is free: https://firms.modaps.eosdis.nasa.gov/api/map_key/
"""

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

FIRMS_ENDPOINT = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
MAX_DAYS = 5
NRT_SOURCES = ("VIIRS_NOAA21_NRT", "VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT")
ARCHIVE_SOURCES = ("VIIRS_NOAA21_SP", "VIIRS_NOAA20_SP", "VIIRS_SNPP_SP")
_CONFIDENCE = {"l": "low", "n": "nominal", "h": "high"}


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_csv(text: str, source: str) -> list[dict[str, Any]]:
    """FIRMS CSV -> auxiliary event payloads. Rows without a position or time are skipped."""
    if not text.lstrip().lower().startswith("latitude"):
        # Errors come back as plain text with HTTP 200 ("Invalid MAP_KEY.", ...).
        raise AppError(f"FIRMS rejected the request: {text.strip()[:200]}")
    events = []
    for row in csv.DictReader(io.StringIO(text)):
        latitude, longitude = _number(row.get("latitude")), _number(row.get("longitude"))
        date, time = (row.get("acq_date") or "").strip(), (row.get("acq_time") or "").strip()
        if latitude is None or longitude is None or not date or not time.isdigit():
            continue
        stamp = time.zfill(4)
        when = datetime.strptime(f"{date} {stamp}", "%Y-%m-%d %H%M").replace(tzinfo=UTC)
        confidence = (row.get("confidence") or "").strip().lower()
        satellite = (row.get("satellite") or "").strip()
        events.append(
            {
                "source": "FIRMS",
                # FIRMS has no detection id; position + time + satellite is unique.
                "external_id": f"{source}:{date}T{stamp}:{latitude:.5f},{longitude:.5f}:{satellite}",
                "event_type": "FIRE",
                "event_date": when,
                "longitude": longitude,
                "latitude": latitude,
                "magnitude": _number(row.get("frp")),  # fire radiative power, MW
                "metadata": {
                    "collection": source,
                    "frp_mw": _number(row.get("frp")),
                    "brightness_k": _number(row.get("bright_ti4")),
                    "confidence": _CONFIDENCE.get(confidence, confidence or None),
                    "satellite": satellite or None,
                    "daynight": (row.get("daynight") or "").strip() or None,
                },
            }
        )
    return events


class FirmsClient:
    @property
    def configured(self) -> bool:
        return bool(settings.firms_api_key)

    def _fetch(self, client: httpx.Client, source: str, bbox, start: datetime, days: int):
        west, south, east, north = bbox
        area = f"{west:.4f},{south:.4f},{east:.4f},{north:.4f}"
        url = f"{FIRMS_ENDPOINT}/{settings.firms_api_key}/{source}/{area}/{days}/{start:%Y-%m-%d}"
        response = client.get(url)
        response.raise_for_status()
        return parse_csv(response.text, source)

    def fetch_events(
        self,
        *,
        bbox: tuple[float, float, float, float],
        start: datetime,
        end: datetime,
        timeout: float = 60.0,
    ) -> list[dict[str, Any]]:
        if not self.configured:
            raise AppError("FIRMS_API_KEY is not set")
        events: dict[str, dict[str, Any]] = {}
        answered: set[str] = set()
        failures: dict[str, str] = {}
        with httpx.Client(timeout=timeout) as client:
            for sources in (NRT_SOURCES, ARCHIVE_SOURCES):
                cursor = start
                while cursor.date() <= end.date():
                    days = min(MAX_DAYS, (end.date() - cursor.date()).days + 1)
                    for source in sources:
                        if source in failures:
                            continue  # do not repeat a request that cannot work
                        try:
                            found = self._fetch(client, source, bbox, cursor, days)
                        except (AppError, httpx.HTTPError) as exc:
                            failures[source] = str(exc)
                            logger.warning("FIRMS collection %s unavailable: %s", source, exc)
                            continue
                        answered.add(source)
                        for event in found:
                            events[event["external_id"]] = event
                    cursor += timedelta(days=days)
                if events:
                    break
        if not answered:
            raise AppError(
                "no FIRMS collection answered: " + "; ".join(sorted(set(failures.values())))[:300]
            )
        logger.info("FIRMS returned %s detections for bbox=%s", len(events), bbox)
        return list(events.values())
