"""USGS earthquake catalogue (public, no API key)."""

from datetime import datetime
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

USGS_ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"


class UsgsClient:
    def fetch_events(
        self,
        *,
        bbox: tuple[float, float, float, float],
        start: datetime,
        end: datetime,
        min_magnitude: float = 3.0,
        limit: int = 500,
        timeout: float = 30.0,
    ) -> list[dict[str, Any]]:
        minx, miny, maxx, maxy = bbox
        params = {
            "format": "geojson",
            "starttime": start.date().isoformat(),
            "endtime": end.date().isoformat(),
            "minmagnitude": min_magnitude,
            "minlatitude": miny,
            "maxlatitude": maxy,
            "minlongitude": minx,
            "maxlongitude": maxx,
            "limit": limit,
            "orderby": "time",
        }
        with httpx.Client(timeout=timeout) as client:
            response = client.get(USGS_ENDPOINT, params=params)
            response.raise_for_status()
            payload = response.json()

        events = []
        for feature in payload.get("features", []):
            properties = feature.get("properties") or {}
            lon, lat = (feature.get("geometry") or {}).get("coordinates", [None, None])[:2]
            if lat is None or lon is None:
                continue
            events.append(
                {
                    "source": "USGS",
                    "external_id": feature.get("id"),
                    "event_type": "EARTHQUAKE",
                    "event_date": datetime.fromtimestamp(properties["time"] / 1000).astimezone(),
                    "longitude": lon,
                    "latitude": lat,
                    "magnitude": properties.get("mag"),
                    "metadata": properties,
                }
            )
        logger.info("USGS returned %s events for bbox=%s", len(events), bbox)
        return events
