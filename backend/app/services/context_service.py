"""Live context for any point on Earth, straight from the public catalogues.

Unlike the analysis pipeline, nothing here needs an ingested scene or a stored
location: give a latitude/longitude and a time window and get what NISAR has
acquired there, and which earthquakes, fires and rain happened around it.

    nisar          products over the point, freshness per level, comparable pairs
    earthquakes    USGS events within a radius, with distance to the point
    precipitation  NASA POWER daily series, total and anomaly
    fires          NASA FIRMS detections within a radius
    timeline       all of the above merged by date

Every answer says where it came from (`source`, `endpoint`) and when
(`retrieved_at`). Results are cached for a few minutes.
"""

import math
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import httpx

from app.core import cache
from app.core.config import settings
from app.core.exceptions import AppError, UpstreamError
from app.core.logging import get_logger
from app.integrations.auxiliary.firms_client import FIRMS_ENDPOINT, FirmsClient
from app.integrations.auxiliary.power_client import PowerClient
from app.integrations.auxiliary.usgs_client import USGS_ENDPOINT, UsgsClient
from app.integrations.nisar.asf_client import AsfClient

logger = get_logger(__name__)

ASF_ENDPOINT = "https://api.daac.asf.alaska.edu/services/search/param"
MAX_FIRE_DAYS = 31  # FIRMS serves 5 days per request and per collection
MAX_FIRE_DELTA_DEG = 5.0
HEAVY_RAIN_DAY_MM = 20.0
EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((phi2 - phi1) / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def resolve_window(days: int, start: date | None, end: date | None) -> tuple[date, date]:
    """Explicit dates win; otherwise the last `days` days up to today (UTC)."""
    last = end or datetime.now(UTC).date()
    first = start or last - timedelta(days=days - 1)
    if first > last:
        raise AppError("start must not be after end")
    return first, last


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time(), tzinfo=UTC)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _age_days(timestamp: str | None) -> int | None:
    if not timestamp:
        return None
    try:
        moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, (datetime.now(UTC) - moment).days)


def _preview(urls: list[str] | None) -> str | None:
    urls = urls or []
    for suffix in ("_LATLON.png", "_NATIVE.png"):
        for url in urls:
            if url.endswith(suffix):
                return url
    return next((url for url in urls if url.endswith(".png")), None)


def _size_gb(sizes: Any) -> float | None:
    """ASF lists every file of the product; the science file is the big .h5."""
    if not isinstance(sizes, dict):
        return None
    main = [
        info.get("bytes", 0)
        for name, info in sizes.items()
        if name.endswith(".h5") and "QA_STATS" not in name and isinstance(info, dict)
    ]
    return round(sum(main) / 1e9, 2) if main else None


def _polarization(product: dict[str, Any]) -> list[str] | None:
    value = product.get("polarization") or product.get("mainBandPolarization")
    if not value:
        return None
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def trim_granule(product: dict[str, Any]) -> dict[str, Any]:
    start = product.get("startTime")
    return {
        "product_id": product.get("sceneName") or product.get("fileID"),
        "level": product.get("processingLevel"),
        "track": product.get("pathNumber"),
        "frame": product.get("frameNumber"),
        "flight_direction": product.get("flightDirection"),
        "polarization": _polarization(product),
        "processing_version": product.get("crid"),
        "start": start,
        "stop": product.get("stopTime"),
        "age_days": _age_days(start),
        "size_gb": _size_gb(product.get("bytes")),
        "browse_png": _preview(product.get("browse")),
        "download_url": product.get("url"),
        "footprint": product.get("geometry"),
    }


def comparable_pairs(granules: list[dict[str, Any]], limit: int = 25) -> list[dict[str, Any]]:
    """Consecutive GCOV acquisitions of the same track, frame, direction and polarisation.

    These are the before/after pairs the change analysis can use directly.
    """
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for granule in granules:
        if granule["level"] != "GCOV" or not granule["start"]:
            continue
        key = (
            granule["track"],
            granule["frame"],
            granule["flight_direction"],
            tuple(granule["polarization"] or ()),
        )
        groups[key].append(granule)

    pairs = []
    for (track, frame, direction, polarization), members in groups.items():
        members.sort(key=lambda g: g["start"])
        for before, after in zip(members, members[1:], strict=False):
            first = datetime.fromisoformat(before["start"].replace("Z", "+00:00"))
            second = datetime.fromisoformat(after["start"].replace("Z", "+00:00"))
            interval = round((second - first).total_seconds() / 86400.0, 1)
            if interval < 1:
                continue  # two files of one pass, not two dates
            pairs.append(
                {
                    "track": track,
                    "frame": frame,
                    "flight_direction": direction,
                    "polarization": list(polarization),
                    "before": {"product_id": before["product_id"], "start": before["start"]},
                    "after": {"product_id": after["product_id"], "start": after["start"]},
                    "interval_days": interval,
                    "same_processing_version": before["processing_version"]
                    == after["processing_version"],
                    "download_gb": round((before["size_gb"] or 0) + (after["size_gb"] or 0), 2),
                }
            )
    pairs.sort(key=lambda pair: pair["after"]["start"], reverse=True)
    return pairs[:limit]


class ContextService:
    def __init__(
        self,
        asf: AsfClient | None = None,
        usgs: UsgsClient | None = None,
        power: PowerClient | None = None,
        firms: FirmsClient | None = None,
    ) -> None:
        self.asf = asf or AsfClient()
        self.usgs = usgs or UsgsClient()
        self.power = power or PowerClient()
        self.firms = firms or FirmsClient()

    def _cached(self, kind: str, parts: tuple, produce):
        key = f"{kind}:" + ":".join(str(part) for part in parts)
        try:
            return cache.cached(key, settings.context_cache_ttl, produce)
        except AppError:
            raise
        except (httpx.HTTPError, Exception) as exc:  # network, quota, upstream format
            logger.warning("%s lookup failed: %s", kind, exc)
            raise UpstreamError(f"{kind} source did not answer: {str(exc)[:200]}") from exc

    # --- NISAR ---------------------------------------------------------------

    def nisar(
        self,
        *,
        latitude: float,
        longitude: float,
        days: int = 120,
        start: date | None = None,
        end: date | None = None,
        level: str | None = None,
        max_results: int = 100,
    ) -> dict[str, Any]:
        first, last = resolve_window(days, start, end)
        level = None if not level or level.upper() == "ALL" else level.upper()

        def produce() -> dict[str, Any]:
            products = self.asf.search_point(
                longitude=longitude,
                latitude=latitude,
                start=_midnight(first),
                end=_midnight(last) + timedelta(days=1),
                processing_level=level,
                max_results=max_results,
            )
            granules = sorted(
                (trim_granule(product) for product in products),
                key=lambda g: g["start"] or "",
                reverse=True,
            )
            latest: dict[str, dict[str, Any]] = {}
            counts: dict[str, int] = defaultdict(int)
            for granule in granules:  # newest first
                counts[granule["level"]] += 1
                latest.setdefault(
                    granule["level"],
                    {
                        "product_id": granule["product_id"],
                        "start": granule["start"],
                        "age_days": granule["age_days"],
                    },
                )
            return {
                "source": "ASF DAAC (NISAR)",
                "endpoint": ASF_ENDPOINT,
                "retrieved_at": _now(),
                "query": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "start": first.isoformat(),
                    "end": last.isoformat(),
                    "level": level or "ALL",
                },
                "total": len(granules),
                "truncated": len(granules) >= max_results,
                "count_by_level": dict(counts),
                "latest_by_level": latest,
                "has_gcov": "GCOV" in counts,
                "comparable_pairs": comparable_pairs(granules),
                "granules": granules,
            }

        return self._cached("nisar", (latitude, longitude, first, last, level, max_results), produce)

    # --- earthquakes ---------------------------------------------------------

    def earthquakes(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float = 250.0,
        days: int = 30,
        start: date | None = None,
        end: date | None = None,
        min_magnitude: float = 2.5,
    ) -> dict[str, Any]:
        first, last = resolve_window(days, start, end)

        def produce() -> dict[str, Any]:
            events = self.usgs.fetch_radius(
                longitude=longitude,
                latitude=latitude,
                radius_km=radius_km,
                start=_midnight(first),
                end=_midnight(last) + timedelta(days=1),  # USGS endtime is exclusive
                min_magnitude=min_magnitude,
            )
            data = []
            for event in events:
                properties = event.get("metadata") or {}
                data.append(
                    {
                        "id": event["external_id"],
                        "time": _iso(event["event_date"]),
                        "magnitude": event["magnitude"],
                        "depth_km": event.get("depth_km"),
                        "place": properties.get("place"),
                        "latitude": event["latitude"],
                        "longitude": event["longitude"],
                        "distance_km": round(
                            haversine_km(latitude, longitude, event["latitude"], event["longitude"]), 1
                        ),
                        "url": properties.get("url"),
                    }
                )
            data.sort(key=lambda item: item["time"], reverse=True)
            magnitudes = [item["magnitude"] for item in data if item["magnitude"] is not None]
            return {
                "source": "USGS FDSN",
                "endpoint": USGS_ENDPOINT,
                "retrieved_at": _now(),
                "query": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_km": radius_km,
                    "start": first.isoformat(),
                    "end": last.isoformat(),
                    "min_magnitude": min_magnitude,
                },
                "total": len(data),
                "max_magnitude": max(magnitudes) if magnitudes else None,
                "nearest": min(data, key=lambda item: item["distance_km"]) if data else None,
                "strongest": max(
                    (item for item in data if item["magnitude"] is not None),
                    key=lambda item: item["magnitude"],
                    default=None,
                ),
                "data": data,
            }

        return self._cached(
            "earthquakes", (latitude, longitude, radius_km, first, last, min_magnitude), produce
        )

    # --- precipitation -------------------------------------------------------

    def precipitation(
        self,
        *,
        latitude: float,
        longitude: float,
        days: int = 30,
        start: date | None = None,
        end: date | None = None,
    ) -> dict[str, Any]:
        # POWER publishes with about two days of latency.
        default_end = datetime.now(UTC).date() - timedelta(days=2)
        first, last = resolve_window(days, start, end or default_end)

        def produce() -> dict[str, Any]:
            series = self.power.fetch_series(
                longitude=longitude, latitude=latitude, start=first, end=last
            )
            base = {
                "source": "NASA POWER (PRECTOTCORR)",
                "retrieved_at": _now(),
                "query": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "start": first.isoformat(),
                    "end": last.isoformat(),
                },
                "units": "mm/day",
                "grid": "0.5 x 0.625 deg",
            }
            if series is None:
                return {**base, "endpoint": None, "available": False, "series": []}
            daily = series.pop("daily_mm")
            return {
                **base,
                "endpoint": series.pop("endpoint"),
                "available": True,
                "elevation_m": series.pop("elevation_m"),
                **series,
                "series": [{"date": day, "mm": value} for day, value in daily.items()],
            }

        return self._cached("precipitation", (latitude, longitude, first, last), produce)

    # --- fires ---------------------------------------------------------------

    def fires(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
        days: int = 5,
        start: date | None = None,
        end: date | None = None,
    ) -> dict[str, Any]:
        first, last = resolve_window(days, start, end)
        if (last - first).days + 1 > MAX_FIRE_DAYS:
            raise AppError(f"fire lookups cover at most {MAX_FIRE_DAYS} days per request")
        if not self.firms.configured:
            raise UpstreamError("FIRMS_API_KEY is not set: fires cannot be queried")

        def produce() -> dict[str, Any]:
            delta_lat = min(radius_km / 111.0, MAX_FIRE_DELTA_DEG)
            delta_lon = min(
                radius_km / (111.0 * max(math.cos(math.radians(latitude)), 0.1)), MAX_FIRE_DELTA_DEG
            )
            bbox = (
                max(-180.0, longitude - delta_lon),
                max(-90.0, latitude - delta_lat),
                min(180.0, longitude + delta_lon),
                min(90.0, latitude + delta_lat),
            )
            events = self.firms.fetch_events(bbox=bbox, start=_midnight(first), end=_midnight(last))
            data = []
            for event in events:
                distance = haversine_km(latitude, longitude, event["latitude"], event["longitude"])
                if distance > radius_km:
                    continue
                metadata = event.get("metadata") or {}
                data.append(
                    {
                        "time": _iso(event["event_date"]),
                        "latitude": event["latitude"],
                        "longitude": event["longitude"],
                        "distance_km": round(distance, 2),
                        "frp_mw": event["magnitude"],
                        "confidence": metadata.get("confidence"),
                        "satellite": metadata.get("satellite"),
                        "collection": metadata.get("collection"),
                        "daynight": metadata.get("daynight"),
                    }
                )
            data.sort(key=lambda item: item["time"], reverse=True)
            power = [item["frp_mw"] for item in data if item["frp_mw"] is not None]
            by_day: dict[str, int] = defaultdict(int)
            for item in data:
                by_day[item["time"][:10]] += 1
            return {
                "source": "NASA FIRMS (VIIRS)",
                "endpoint": FIRMS_ENDPOINT,
                "retrieved_at": _now(),
                "query": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_km": radius_km,
                    "start": first.isoformat(),
                    "end": last.isoformat(),
                },
                "total": len(data),
                "max_frp_mw": max(power) if power else None,
                "total_frp_mw": round(sum(power), 1) if power else 0.0,
                "detections_by_day": dict(sorted(by_day.items())),
                "data": data,
            }

        return self._cached("fires", (latitude, longitude, radius_km, first, last), produce)

    # --- timeline ------------------------------------------------------------

    def timeline(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float = 100.0,
        days: int = 30,
        start: date | None = None,
        end: date | None = None,
        min_magnitude: float = 2.5,
    ) -> dict[str, Any]:
        """Everything that happened around the point, by date. A source that fails is reported, not fatal."""
        first, last = resolve_window(days, start, end)
        events: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        common = {"latitude": latitude, "longitude": longitude, "start": first, "end": last}

        def attempt(name: str, call, convert) -> None:
            try:
                payload = call()
                added = convert(payload)
                events.extend(added)
                sources.append(
                    {
                        "source": payload.get("source", name),
                        "status": "ok",
                        "events": len(added),
                        "retrieved_at": payload.get("retrieved_at"),
                        "endpoint": payload.get("endpoint"),
                    }
                )
            except AppError as exc:
                sources.append({"source": name, "status": "error", "events": 0, "detail": exc.message})

        attempt(
            "ASF DAAC (NISAR)",
            lambda: self.nisar(**common, level="GCOV"),
            lambda payload: [
                {
                    "date": granule["start"],
                    "kind": "nisar",
                    "title": f"Adquisición NISAR GCOV (track {granule['track']}, frame {granule['frame']})",
                    "product_id": granule["product_id"],
                    "browse_png": granule["browse_png"],
                }
                for granule in payload["granules"]
            ],
        )
        attempt(
            "USGS FDSN",
            lambda: self.earthquakes(**common, radius_km=radius_km, min_magnitude=min_magnitude),
            lambda payload: [
                {
                    "date": item["time"],
                    "kind": "earthquake",
                    "title": f"Sismo M{item['magnitude']:.1f}"
                    if item["magnitude"] is not None
                    else "Sismo",
                    "detail": item["place"],
                    "magnitude": item["magnitude"],
                    "distance_km": item["distance_km"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                }
                for item in payload["data"]
            ],
        )
        attempt(
            "NASA POWER (PRECTOTCORR)",
            lambda: self.precipitation(
                latitude=latitude,
                longitude=longitude,
                start=first,
                end=min(last, datetime.now(UTC).date() - timedelta(days=2)),
            )
            if first <= datetime.now(UTC).date() - timedelta(days=2)
            else {"source": "NASA POWER (PRECTOTCORR)", "series": []},
            lambda payload: [
                {
                    "date": f"{point['date']}T12:00:00+00:00",
                    "kind": "precipitation",
                    "title": f"Lluvia intensa: {point['mm']:.0f} mm en el día",
                    "mm": point["mm"],
                }
                for point in payload["series"]
                if point["mm"] is not None and point["mm"] >= HEAVY_RAIN_DAY_MM
            ],
        )
        fire_first = max(first, last - timedelta(days=MAX_FIRE_DAYS - 1))
        attempt(
            "NASA FIRMS (VIIRS)",
            lambda: self.fires(
                latitude=latitude,
                longitude=longitude,
                radius_km=min(radius_km, 100.0),
                start=fire_first,
                end=last,
            ),
            lambda payload: [
                {
                    "date": f"{day}T12:00:00+00:00",
                    "kind": "fire",
                    "title": f"{count} foco(s) de fuego activo",
                    "detections": count,
                }
                for day, count in payload["detections_by_day"].items()
            ],
        )

        events.sort(key=lambda event: event["date"] or "", reverse=True)
        return {
            "query": {
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km,
                "start": first.isoformat(),
                "end": last.isoformat(),
            },
            "generated_at": _now(),
            "total": len(events),
            "count_by_kind": {
                kind: sum(1 for event in events if event["kind"] == kind)
                for kind in ("nisar", "earthquake", "precipitation", "fire")
            },
            "sources": sources,
            "events": events,
        }
