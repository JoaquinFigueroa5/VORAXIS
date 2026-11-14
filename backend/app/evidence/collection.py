"""Fetch the auxiliary events an analysis needs and store the new ones.

Each source reports what happened to it, so the API can say "no fires were
found" apart from "fires could not be checked". A source that fails never fails
the analysis: the change map is still valid without context.
"""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from shapely.geometry import box

from app.core.logging import get_logger
from app.evidence.profiles import FETCH_MARGIN_DEG, MAX_PRECIPITATION_CELLS, PROFILES
from app.integrations.auxiliary.firms_client import FirmsClient
from app.integrations.auxiliary.power_client import PowerClient, cell_bounds
from app.integrations.auxiliary.usgs_client import UsgsClient
from app.repositories.evidence_repository import EvidenceRepository

logger = get_logger(__name__)

Bbox = tuple[float, float, float, float]


def _expand(bbox: Bbox, margin: float) -> Bbox:
    west, south, east, north = bbox
    return (
        max(-180.0, west - margin),
        max(-90.0, south - margin),
        min(180.0, east + margin),
        min(90.0, north + margin),
    )


def _store(db, repo: EvidenceRepository, events: list[dict[str, Any]]) -> int:
    inserted = 0
    for event in events:
        if event.get("external_id") and repo.find_auxiliary(
            db, source=event["source"], external_id=event["external_id"]
        ):
            continue
        geometry_wkt = box(*event["bbox"]).wkt if event.get("bbox") else None
        repo.add_auxiliary(
            db,
            source=event["source"],
            external_id=event.get("external_id"),
            event_type=event["event_type"],
            event_date=event["event_date"],
            longitude=event.get("longitude"),
            latitude=event.get("latitude"),
            geometry_wkt=geometry_wkt,
            magnitude=event.get("magnitude"),
            metadata=event.get("metadata"),
        )
        inserted += 1
    db.commit()
    return inserted


def precipitation_cells(points: list[tuple[float, float, float]]) -> list[tuple[float, float]]:
    """Centres of the grid cells holding most changed area. `points`: (lon, lat, weight)."""
    weights: Counter[Bbox] = Counter()
    for longitude, latitude, weight in points:
        weights[cell_bounds(longitude, latitude)] += weight
    return [
        ((west + east) / 2, (south + north) / 2)
        for (west, south, east, north), _ in weights.most_common(MAX_PRECIPITATION_CELLS)
    ]


def collect(
    db,
    *,
    bbox: Bbox,
    points: list[tuple[float, float, float]],
    before: datetime,
    after: datetime,
    usgs: UsgsClient | None = None,
    firms: FirmsClient | None = None,
    power: PowerClient | None = None,
) -> dict[str, dict[str, Any]]:
    """Query USGS, FIRMS and POWER for the interval between the two acquisitions."""
    repo = EvidenceRepository()
    usgs, firms, power = usgs or UsgsClient(), firms or FirmsClient(), power or PowerClient()
    report: dict[str, dict[str, Any]] = {}

    def attempt(name: str, event_type: str, fetch) -> None:
        try:
            events = fetch()
            report[name] = {
                "status": "ok",
                "event_type": event_type,
                "events_found": len(events),
                "events_stored": _store(db, repo, events),
            }
        except Exception as exc:  # network, quota, bad key: context is optional
            db.rollback()
            logger.warning("%s lookup failed: %s", name, exc)
            report[name] = {"status": "error", "event_type": event_type, "detail": str(exc)[:300]}

    quake = PROFILES["EARTHQUAKE"]
    attempt(
        "USGS",
        "EARTHQUAKE",
        lambda: usgs.fetch_events(
            bbox=_expand(bbox, FETCH_MARGIN_DEG["EARTHQUAKE"]),
            start=before - timedelta(days=quake.lead_days),
            # USGS `endtime` is exclusive at day granularity.
            end=after + timedelta(days=1),
        ),
    )

    if firms.configured:
        fire = PROFILES["FIRE"]
        attempt(
            "FIRMS",
            "FIRE",
            lambda: firms.fetch_events(
                bbox=_expand(bbox, FETCH_MARGIN_DEG["FIRE"]),
                start=before - timedelta(days=fire.lead_days),
                end=after,
            ),
        )
    else:
        report["FIRMS"] = {
            "status": "skipped",
            "event_type": "FIRE",
            "detail": "FIRMS_API_KEY is not set",
        }

    rain = PROFILES["PRECIPITATION"]

    def fetch_rain() -> list[dict[str, Any]]:
        events = []
        for longitude, latitude in precipitation_cells(points):
            event = power.fetch_event(
                longitude=longitude,
                latitude=latitude,
                start=before - timedelta(days=rain.lead_days),
                end=after,
            )
            if event is not None:
                events.append(event)
        return events

    attempt("POWER", "PRECIPITATION", fetch_rain)
    return report
