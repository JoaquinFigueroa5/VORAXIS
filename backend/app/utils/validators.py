from datetime import datetime

from app.core.exceptions import AppError
from app.utils.dates import parse_datetime


def ensure_date_range(start: str | None, end: str | None) -> tuple[datetime | None, datetime | None]:
    parsed_start = parse_datetime(start)
    parsed_end = parse_datetime(end)
    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise AppError("start must be before end")
    return parsed_start, parsed_end


def require(value: object, field: str) -> None:
    if value in (None, ""):
        raise AppError(f"{field} is required")
