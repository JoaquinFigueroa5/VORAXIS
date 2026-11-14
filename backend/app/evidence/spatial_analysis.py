"""Spatial relation between a change polygon and auxiliary events."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auxiliary_event import AuxiliaryEvent
from app.models.change_event import ChangeEvent


def find_candidates(
    db: Session,
    *,
    change_id,
    reference_date,
    radius_km: float,
    window_hours: float,
):
    """Auxiliary events within `radius_km` and +/-`window_hours` of the acquisition.

    ST_DistanceSphere gives metres on EPSG:4326 without a geography cast.
    """
    distance_m = func.ST_DistanceSphere(ChangeEvent.geometry, AuxiliaryEvent.geometry)
    within_time = func.abs(
        func.extract("epoch", AuxiliaryEvent.event_date - reference_date)
    ) <= window_hours * 3600.0

    stmt = (
        select(
            AuxiliaryEvent,
            distance_m.label("distance_m"),
            func.ST_Intersects(ChangeEvent.geometry, AuxiliaryEvent.geometry).label("intersects"),
            func.extract("epoch", AuxiliaryEvent.event_date - reference_date).label("seconds"),
        )
        .join(ChangeEvent, ChangeEvent.id == change_id)
        .where(distance_m <= radius_km * 1000.0, within_time)
        .order_by(distance_m)
        .limit(50)
    )
    return db.execute(stmt).all()
