"""Evidence engine: fetch context, link it to each change, propose a change type.

    1. collect   USGS / FIRMS / POWER for the interval between the acquisitions
    2. link      each change <-> nearby events, per-type radius and lead time
    3. classify  radar signature + linked evidence -> tentative change_type
"""

from sqlalchemy import func, select

from app.core.logging import get_logger
from app.evidence import (
    classification,
    collection,
    interpretation,
    scoring,
    spatial_analysis,
    temporal_analysis,
)
from app.evidence.profiles import PROFILES, window
from app.models.change_event import ChangeEvent
from app.models.observation import Observation
from app.repositories.evidence_repository import EvidenceRepository

logger = get_logger(__name__)


def _extent(db, job_id):
    """(bbox, [(lon, lat, area)]) of the job's changes."""
    extent = func.ST_Extent(ChangeEvent.geometry)
    row = db.execute(
        select(
            func.ST_XMin(extent), func.ST_YMin(extent), func.ST_XMax(extent), func.ST_YMax(extent)
        ).where(ChangeEvent.job_id == job_id)
    ).one()
    points = db.execute(
        select(
            func.ST_X(func.ST_Centroid(ChangeEvent.geometry)),
            func.ST_Y(func.ST_Centroid(ChangeEvent.geometry)),
            func.coalesce(ChangeEvent.area_km2, 0.0),
        ).where(ChangeEvent.job_id == job_id)
    ).all()
    return tuple(float(v) for v in row), [(float(x), float(y), float(a)) for x, y, a in points]


def link(db, change_id, before, after) -> list[dict]:
    """Store evidence records for one change; returns them in classifier form."""
    evidence = EvidenceRepository()
    linked = []
    for profile in PROFILES.values():
        start, end = window(profile, before, after)
        scored = []
        for event, distance_m, intersects in spatial_analysis.find_candidates(
            db,
            change_id=change_id,
            event_type=profile.event_type,
            start=start,
            end=end,
            radius_km=profile.radius_km,
        ):
            distance_km = float(distance_m) / 1000.0
            # A precipitation event stands for its whole window (lead time included);
            # its date is only the wettest day, so it must not be judged as an instant.
            event_date = event.event_date
            if profile.event_type == "PRECIPITATION":
                event_date = min(max(event_date, before), after)
            value = scoring.score(
                distance_km=distance_km,
                radius_km=profile.radius_km,
                event_date=event_date,
                before=before,
                after=after,
                lead_days=profile.lead_days,
                event_strength=scoring.strength(
                    event.event_type, event.magnitude, event.extra_metadata
                ),
            )
            scored.append((value, distance_km, bool(intersects), event))
        scored.sort(key=lambda item: item[0], reverse=True)
        for value, distance_km, intersects, event in scored[: profile.max_links]:
            hours = temporal_analysis.hours_between(after, event.event_date)
            relation = "INTERSECTS" if intersects else "NEAR"
            evidence.add(
                db,
                change_event_id=change_id,
                auxiliary_event_id=event.id,
                spatial_relation=relation,
                distance_km=round(distance_km, 3),
                time_difference_hours=round(hours, 3),
                evidence_score=value,
                explanation=interpretation.explain(
                    source=event.source,
                    event_type=event.event_type,
                    distance_km=distance_km,
                    hours=hours,
                    intersects=intersects,
                    relation=relation,
                    magnitude=event.magnitude,
                    metadata=event.extra_metadata,
                ),
            )
            linked.append(
                {
                    "event_type": event.event_type,
                    "score": value,
                    "magnitude": event.magnitude,
                    "metadata": event.extra_metadata,
                }
            )
    return linked


def run(db, context) -> None:
    if not context.change_event_ids:
        return
    before = db.get(Observation, context.before_observation_id)
    after = db.get(Observation, context.after_observation_id)
    if before is None or after is None:
        return

    if context.parameters.get("fetch_auxiliary", True):
        bbox, points = _extent(db, context.job_id)
        context.evidence_sources = collection.collect(
            db,
            bbox=bbox,
            points=points,
            before=before.acquisition_date,
            after=after.acquisition_date,
        )

    records = 0
    types: dict[str, int] = {}
    for change_id in context.change_event_ids:
        linked = link(db, change_id, before.acquisition_date, after.acquisition_date)
        records += len(linked)
        region = context.change_features.get(change_id)
        if region is None:
            continue
        result = classification.classify(
            direction=region.direction,
            mean_change_db=region.mean_change_db,
            before_db=region.mean_before_db,
            after_db=region.mean_after_db,
            polarization=context.polarization,
            evidence=linked,
        )
        change = db.get(ChangeEvent, change_id)
        change.change_type = result.change_type
        change.classification = {
            "type": result.change_type,
            "confidence": result.confidence,
            "reasons": result.reasons,
        }
        types[result.change_type] = types.get(result.change_type, 0) + 1

    context.change_types = types
    db.commit()
    logger.info(
        "job %s linked %s evidence records; change types: %s", context.job_id, records, types
    )
