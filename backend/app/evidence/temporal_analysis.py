from datetime import datetime


def hours_between(reference: datetime, event_date: datetime) -> float:
    """Signed hours from `reference` to `event_date` (negative = event before)."""
    return (event_date - reference).total_seconds() / 3600.0
