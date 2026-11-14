import numpy as np

from app.core.exceptions import ProcessingError
from app.processing.context import JobContext, LoadedRaster


def require_pair_loaded(context: JobContext) -> tuple[LoadedRaster, LoadedRaster]:
    if context.before is None or context.after is None:
        raise ProcessingError("preprocessing did not load both rasters")
    return context.before, context.after


def valid_mask(before: LoadedRaster, after: LoadedRaster) -> np.ndarray:
    return ~(before.invalid | after.invalid)


def valid_pixel_percentage(before: LoadedRaster, after: LoadedRaster) -> float:
    valid = valid_mask(before, after)
    if valid.size == 0:
        return 0.0
    return float(valid.sum() / valid.size * 100.0)


def run(db, context: JobContext) -> None:
    before, after = require_pair_loaded(context)
    percentage = valid_pixel_percentage(before, after)
    context.valid_pixel_percentage = percentage
    if percentage < context.minimum_valid_pixel_percentage:
        raise ProcessingError(
            f"valid pixel percentage {percentage:.1f}% is below the requested "
            f"{context.minimum_valid_pixel_percentage:.1f}%"
        )
