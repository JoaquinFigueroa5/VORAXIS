"""Change detection dispatch: pick the product algorithm, then clean the mask."""

from app.core.exceptions import ProcessingError
from app.processing.algorithms import require_supported
from app.processing.quality_control import require_pair_loaded, valid_mask
from app.processing.segmentation import clean_mask


def run(db, context) -> None:
    before, after = require_pair_loaded(context)
    algorithm = require_supported(context.product_type)

    valid = valid_mask(before, after)
    if not valid.any():
        raise ProcessingError("no overlapping valid pixels between the two observations")

    difference, flagged, threshold, baseline = algorithm.detect(
        before.array,
        after.array,
        valid,
        context.threshold_sigma,
        units=before.units,
        smoothing_window=context.smoothing_window,
        noise_floor_db=context.noise_floor_db,
        edge_buffer_pixels=context.edge_buffer_pixels,
    )
    flagged = clean_mask(flagged)

    context.difference = difference
    context.change_mask = flagged
    context.threshold_db = threshold
    context.baseline_db = baseline
    context.changed_fraction = float(flagged.sum() / valid.sum())
    context.valid_pixel_percentage = float(valid.sum() / valid.size * 100.0)
