"""Evidence engine: link detected changes with auxiliary events.

Defaults are explicit and configurable in code because the right radius/window
depends on the phenomenon being investigated.
"""

from app.core.logging import get_logger
from app.evidence import interpretation, scoring, spatial_analysis, temporal_analysis
from app.models.observation import Observation
from app.repositories.evidence_repository import EvidenceRepository

logger = get_logger(__name__)

RADIUS_KM = 50.0
WINDOW_HOURS = 72.0


def run(db, context) -> None:
    if not context.change_event_ids:
        return

    after = db.get(Observation, context.after_observation_id)
    if after is None:
        return

    evidence = EvidenceRepository()
    linked = 0
    for change_id in context.change_event_ids:
        for event, distance_m, intersects, seconds in spatial_analysis.find_candidates(
            db,
            change_id=change_id,
            reference_date=after.acquisition_date,
            radius_km=RADIUS_KM,
            window_hours=WINDOW_HOURS,
        ):
            distance_km = float(distance_m) / 1000.0
            hours = temporal_analysis.hours_between(after.acquisition_date, event.event_date)
            relation = "INTERSECTS" if intersects else "NEAR"
            evidence.add(
                db,
                change_event_id=change_id,
                auxiliary_event_id=event.id,
                spatial_relation=relation,
                distance_km=round(distance_km, 3),
                time_difference_hours=round(hours, 3),
                evidence_score=scoring.score(
                    distance_km=distance_km,
                    radius_km=RADIUS_KM,
                    hours=hours,
                    window_hours=WINDOW_HOURS,
                ),
                explanation=interpretation.explain(
                    source=event.source,
                    event_type=event.event_type,
                    distance_km=distance_km,
                    hours=hours,
                    intersects=bool(intersects),
                    relation=relation,
                ),
            )
            linked += 1

    db.commit()
    logger.info("job %s linked %s evidence records", context.job_id, linked)
