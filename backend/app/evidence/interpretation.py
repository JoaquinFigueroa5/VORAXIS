"""Human-readable, deliberately cautious explanations."""

from typing import Any

_EVENT_LABELS = {
    "EARTHQUAKE": "earthquake",
    "FIRE": "active fire detection",
    "PRECIPITATION": "precipitation",
}


def _detail(event_type: str, magnitude: float | None, metadata: dict[str, Any] | None) -> str:
    metadata = metadata or {}
    kind = event_type.upper()
    if kind == "EARTHQUAKE" and magnitude is not None:
        return f" (M{magnitude:.1f})"
    if kind == "FIRE":
        parts = []
        if magnitude is not None:
            parts.append(f"{magnitude:.1f} MW")
        if metadata.get("confidence"):
            parts.append(f"{metadata['confidence']} confidence")
        return f" ({', '.join(parts)})" if parts else ""
    if kind == "PRECIPITATION" and magnitude is not None:
        text = f" ({magnitude:.0f} mm accumulated"
        if metadata.get("anomaly_pct") is not None:
            text += f", {metadata['anomaly_pct']:+.0f}% vs climatology"
        return text + ")"
    return ""


def explain(
    *,
    source: str,
    event_type: str,
    distance_km: float,
    hours: float,
    intersects: bool,
    relation: str,
    magnitude: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    label = _EVENT_LABELS.get(event_type.upper(), event_type.lower().replace("_", " "))
    when = "before" if hours < 0 else "after"
    proximity = "inside the change area" if intersects else f"{distance_km:.1f} km away"
    return (
        f"{source} {label}{_detail(event_type, magnitude, metadata)} {proximity}, "
        f"{abs(hours):.1f} h {when} the analysed acquisition "
        f"(relation: {relation}). Spatial and temporal coincidence is context for the change, "
        "not a demonstrated cause."
    )
