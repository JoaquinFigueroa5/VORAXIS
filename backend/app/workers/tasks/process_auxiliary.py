from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.integrations.auxiliary.usgs_client import UsgsClient
from app.repositories.evidence_repository import EvidenceRepository
from app.utils.dates import parse_datetime
from app.utils.geometry import parse_bbox

logger = get_logger(__name__)


def run(bbox: str, start: str, end: str, min_magnitude: float = 3.0) -> int:
    """Fetch USGS earthquakes for a bbox/window and store the new ones."""
    events = UsgsClient().fetch_events(
        bbox=parse_bbox(bbox),
        start=parse_datetime(start),
        end=parse_datetime(end),
        min_magnitude=min_magnitude,
    )
    repo = EvidenceRepository()
    inserted = 0
    with SessionLocal() as db:
        for event in events:
            if event["external_id"] and repo.find_auxiliary(
                db, source=event["source"], external_id=event["external_id"]
            ):
                continue
            repo.add_auxiliary(
                db,
                source=event["source"],
                external_id=event["external_id"],
                event_type=event["event_type"],
                event_date=event["event_date"],
                longitude=event["longitude"],
                latitude=event["latitude"],
                magnitude=event["magnitude"],
                metadata=event["metadata"],
            )
            inserted += 1
        db.commit()
    logger.info("stored %s new auxiliary events", inserted)
    return inserted
