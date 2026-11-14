from datetime import UTC, date, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def parse_date(value: str | None) -> date | None:
    """Accepts ``YYYY-MM-DD`` or a full ISO timestamp."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
