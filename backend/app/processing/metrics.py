"""Per-change metrics. Names and units are part of the API contract.

Everything except the three `job_*`/threshold values describes the polygon
itself, not the whole scene.
"""

from app.repositories.change_repository import ChangeRepository

SOURCE = "processing/vectorization.py"


def record(db, context, event, region) -> None:
    changes = ChangeRepository()
    values = {
        # This polygon
        "mean_change_db": (region.mean_change_db, "dB"),
        "peak_change_db": (region.peak_change_db, "dB"),
        "mean_backscatter_before_db": (region.mean_before_db, "dB"),
        "mean_backscatter_after_db": (region.mean_after_db, "dB"),
        "changed_area_km2": (region.area_km2, "km2"),
        "changed_pixel_count": (float(region.pixel_count), "pixels"),
        # The detection that produced it
        "detection_threshold_db": (context.threshold_db or 0.0, "dB"),
        "scene_baseline_shift_db": (context.baseline_db or 0.0, "dB"),
        "job_changed_pixel_fraction": (context.changed_fraction or 0.0, "fraction"),
        "job_valid_pixel_percentage": (context.valid_pixel_percentage or 0.0, "percent"),
    }
    metadata = {
        "polarization": context.polarization,
        "direction": region.direction,
        "threshold_sigma": context.threshold_sigma,
    }
    for name, (value, unit) in values.items():
        changes.add_metric(
            db,
            change_event_id=event.id,
            metric_name=name,
            value=round(float(value), 6),
            unit=unit,
            source=SOURCE,
            metadata=metadata,
        )
