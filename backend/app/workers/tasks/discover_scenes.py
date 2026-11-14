from app.core.database import SessionLocal
from app.services.nisar_service import NisarService
from app.utils.geometry import parse_bbox


def run(bbox: str, start: str | None = None, end: str | None = None) -> int:
    """Sync ASF catalogue hits for a bbox/date window into PostGIS."""
    from app.utils.dates import parse_datetime

    service = NisarService()
    with SessionLocal() as db:
        return service.sync_from_catalogue(
            db,
            bbox=parse_bbox(bbox),
            start=parse_datetime(start),
            end=parse_datetime(end),
        )
