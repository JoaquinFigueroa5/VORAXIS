"""Heuristic evidence score.

``evidence_score = spatial * temporal * strength``, every factor in [0, 1]:

- spatial: 1 at distance 0 km, 0 at the search radius of the event type.
- temporal: 1 when the event falls between the two acquisitions, fading to 0
  across the lead time before the first one.
- strength: how notable the event itself is (magnitude, fire confidence,
  rainfall against climatology).

This is a ranking aid, **not** a calibrated probability. It says "this event is
close in space and time, and it was a notable one", never "this event caused
the change".
"""

from datetime import datetime
from typing import Any


def spatial_factor(distance_km: float, radius_km: float) -> float:
    if radius_km <= 0:
        return 0.0
    return max(0.0, 1.0 - distance_km / radius_km)


def temporal_factor(
    event_date: datetime, before: datetime, after: datetime, lead_days: float
) -> float:
    if before <= event_date <= after:
        return 1.0
    if event_date > after or lead_days <= 0:
        return 0.0
    days_early = (before - event_date).total_seconds() / 86400.0
    return max(0.0, 1.0 - days_early / lead_days)


def strength(event_type: str, magnitude: float | None, metadata: dict[str, Any] | None) -> float:
    metadata = metadata or {}
    kind = event_type.upper()
    if kind == "EARTHQUAKE":
        # M3 is barely felt, M6 damages structures.
        return _clamp(((magnitude or 0.0) - 3.0) / 3.0, low=0.1)
    if kind == "FIRE":
        return {"high": 1.0, "nominal": 0.8, "low": 0.5}.get(metadata.get("confidence"), 0.7)
    if kind == "PRECIPITATION":
        total = float(metadata.get("total_mm") or magnitude or 0.0)
        anomaly = float(metadata.get("anomaly_pct") or 0.0)
        # Half for how much it rained, half for how unusual that is: 150 mm that
        # are normal for the season are context, 150 mm at twice the norm are a signal.
        return _clamp(0.5 * total / 150.0 + 0.5 * max(anomaly, 0.0) / 100.0, low=0.05)
    return 0.5


def score(
    *,
    distance_km: float,
    radius_km: float,
    event_date: datetime,
    before: datetime,
    after: datetime,
    lead_days: float,
    event_strength: float = 1.0,
) -> float:
    value = (
        spatial_factor(distance_km, radius_km)
        * temporal_factor(event_date, before, after, lead_days)
        * event_strength
    )
    return round(value, 4)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
