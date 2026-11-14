"""Spatial relation between a change polygon and auxiliary events."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auxiliary_event import AuxiliaryEvent
from app.models.change_event import ChangeEvent


def find_candidates(
    db: Session,
    *,
    change_id,
    event_type: str,
    start: datetime,
    end: datetime,
    radius_km: float,
    limit: int = 50,
):
    """Events of one type within `radius_km` of the change and dated in [start, end].

    ST_DistanceSphere gives metres on EPSG:4326 without a geography cast; for
    polygon events (precipitation cells) it is 0 when they overlap the change.
    """
    distance_m = func.ST_DistanceSphere(ChangeEvent.geometry, AuxiliaryEvent.geometry)
    stmt = (
        select(
            AuxiliaryEvent,
            distance_m.label("distance_m"),
            func.ST_Intersects(ChangeEvent.geometry, AuxiliaryEvent.geometry).label("intersects"),
        )
        .join(ChangeEvent, ChangeEvent.id == change_id)
        .where(
            AuxiliaryEvent.event_type == event_type,
            AuxiliaryEvent.event_date >= start,
            AuxiliaryEvent.event_date <= end,
            # Cheap index-assisted prefilter in degrees before the exact distance.
            func.ST_DWithin(
                ChangeEvent.geometry, AuxiliaryEvent.geometry, radius_km / 111.0 * 1.5 + 0.01
            ),
            distance_m <= radius_km * 1000.0,
        )
        .order_by(distance_m)
        .limit(limit)
    )
    return db.execute(stmt).all()
