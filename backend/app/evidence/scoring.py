"""Heuristic evidence score.

``evidence_score = spatial * temporal`` with both factors in [0, 1]:

- spatial: 1 at distance 0 km, 0 at the search radius.
- temporal: 1 at 0 h, 0 at the search window.

This is a ranking aid, **not** a calibrated probability. It says "this event is
close in space and time", never "this event caused the change".
"""


def score(*, distance_km: float, radius_km: float, hours: float, window_hours: float) -> float:
    if radius_km <= 0 or window_hours <= 0:
        return 0.0
    spatial = max(0.0, 1.0 - distance_km / radius_km)
    temporal = max(0.0, 1.0 - abs(hours) / window_hours)
    return round(spatial * temporal, 4)
