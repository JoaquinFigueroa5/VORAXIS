"""Human-readable, deliberately cautious explanations."""

_EVENT_LABELS = {
    "EARTHQUAKE": "earthquake",
    "FIRE": "active fire detection",
    "PRECIPITATION": "precipitation",
}


def explain(
    *,
    source: str,
    event_type: str,
    distance_km: float,
    hours: float,
    intersects: bool,
    relation: str,
) -> str:
    label = _EVENT_LABELS.get(event_type.upper(), event_type.lower().replace("_", " "))
    when = "before" if hours < 0 else "after"
    proximity = "inside the change area" if intersects else f"{distance_km:.1f} km away"
    return (
        f"{source} {label} {proximity}, {abs(hours):.1f} h {when} the analysed acquisition "
        f"(relation: {relation}). Spatial and temporal coincidence is context for the change, "
        "not a demonstrated cause."
    )
