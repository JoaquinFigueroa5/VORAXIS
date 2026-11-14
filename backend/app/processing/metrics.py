"""Per-change metrics. Names and units are part of the API contract."""

import numpy as np

from app.core.logging import get_logger
from app.repositories.change_repository import ChangeRepository

logger = get_logger(__name__)


def record(db, context, event) -> None:
    changes = ChangeRepository()
    valid = ~(context.before.invalid | context.after.invalid) if context.before and context.after else None
    if context.difference is None or valid is None:
        return

    values = {
        "mean_absolute_difference": (float(context.difference[valid].mean()), "amplitude"),
        "std_absolute_difference": (float(context.difference[valid].std()), "amplitude"),
        "threshold_sigma": (context.threshold_sigma, "sigma"),
        "changed_pixel_fraction": (context.changed_fraction or 0.0, "fraction"),
        "changed_area_km2": (event.area_km2 or 0.0, "km2"),
        "valid_pixel_percentage": (context.valid_pixel_percentage or 0.0, "percent"),
    }
    for name, (value, unit) in values.items():
        changes.add_metric(
            db,
            change_event_id=event.id,
            metric_name=name,
            value=value,
            unit=unit,
            source="processing/change_detection.py",
            metadata={"polarization": context.polarization},
        )
