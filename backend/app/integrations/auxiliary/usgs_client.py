"""USGS earthquake catalogue (public, no API key)."""

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

USGS_ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"


class UsgsClient:
    def _query(self, params: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(USGS_ENDPOINT, params={"format": "geojson", **params})
            response.raise_for_status()
            payload = response.json()

        events = []
        for feature in payload.get("features", []):
            properties = feature.get("properties") or {}
            coordinates = (feature.get("geometry") or {}).get("coordinates") or []
            lon, lat = (list(coordinates) + [None, None])[:2]
            if lat is None or lon is None or properties.get("time") is None:
                continue
            events.append(
                {
                    "source": "USGS",
                    "external_id": feature.get("id"),
                    "event_type": "EARTHQUAKE",
                    "event_date": datetime.fromtimestamp(properties["time"] / 1000, tz=UTC),
                    "longitude": lon,
                    "latitude": lat,
                    "depth_km": coordinates[2] if len(coordinates) > 2 else None,
                    "magnitude": properties.get("mag"),
                    "metadata": properties,
                }
            )
        return events

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
        events = self._query(
            {
                "starttime": start.date().isoformat(),
                "endtime": end.date().isoformat(),
                "minmagnitude": min_magnitude,
                "minlatitude": miny,
                "maxlatitude": maxy,
                "minlongitude": minx,
                "maxlongitude": maxx,
                "limit": limit,
                "orderby": "time",
            },
            timeout,
        )
        logger.info("USGS returned %s events for bbox=%s", len(events), bbox)
        return events

    def fetch_radius(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_km: float,
        start: datetime,
        end: datetime,
        min_magnitude: float = 2.5,
        limit: int = 500,
        timeout: float = 30.0,
    ) -> list[dict[str, Any]]:
        """Earthquakes within `radius_km` of a point."""
        events = self._query(
            {
                "starttime": start.date().isoformat(),
                "endtime": end.date().isoformat(),
                "minmagnitude": min_magnitude,
                "latitude": latitude,
                "longitude": longitude,
                "maxradiuskm": radius_km,
                "limit": limit,
                "orderby": "time",
            },
            timeout,
        )
        logger.info("USGS returned %s events within %s km", len(events), radius_km)
        return events
