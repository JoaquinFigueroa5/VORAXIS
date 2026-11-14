"""Grid alignment.

Resampling to a shared grid is a real modelling decision (interpolation method,
reference grid) and is not implemented yet. Same-grid pairs pass through, which
covers data already processed to a common UTM grid.
"""

import numpy as np

from app.processing.quality_control import require_pair_loaded


def run(db, context) -> None:
    before, after = require_pair_loaded(context)

    same_crs = before.crs == after.crs
    same_shape = before.array.shape == after.array.shape
    same_transform = np.allclose(
        np.array(before.transform)[:6], np.array(after.transform)[:6], atol=1e-9
    )
    if not (same_crs and same_shape and same_transform):
        raise NotImplementedError(
            "rasters are not on the same grid; resampling/co-registration is not implemented"
        )
