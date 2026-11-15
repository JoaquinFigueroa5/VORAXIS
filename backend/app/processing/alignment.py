"""Grid alignment.

Sources ingested for one AOI already share a grid. When they do not, both are
cropped to their common extent as long as they sit on the same pixel lattice
(same CRS, same resolution, offset by whole pixels). Anything else would need
resampling, which is a modelling decision and is not done silently.
"""

import numpy as np
from rasterio.transform import Affine

from app.core.exceptions import ProcessingError
from app.processing import quality_control
from app.processing.context import LoadedRaster
from app.processing.quality_control import require_pair_loaded

_TOLERANCE = 1e-3  # pixels


def _crop(raster: LoadedRaster, row: int, col: int, rows: int, cols: int) -> None:
    raster.array = raster.array[row : row + rows, col : col + cols]
    raster.invalid = raster.invalid[row : row + rows, col : col + cols]
    raster.transform = raster.transform @ Affine.translation(col, row)
    raster.profile.update(height=rows, width=cols, transform=raster.transform)


def align(before: LoadedRaster, after: LoadedRaster) -> bool:
    """Crop both rasters to their intersection. Returns True when anything was cropped."""
    if before.crs != after.crs:
        raise ProcessingError(
            f"sources use different CRS ({before.crs} vs {after.crs}); ingest both dates "
            "from the same track/frame"
        )
    a, b = before.transform, after.transform
    if not np.allclose((a.a, a.b, a.d, a.e), (b.a, b.b, b.d, b.e), atol=1e-9):
        raise ProcessingError(
            f"sources have different resolutions ({a.a} vs {b.a}); "
            "ingest both dates with the same --multilook"
        )
    # Offset of `after` relative to `before`, in pixels.
    col_shift = (b.c - a.c) / a.a
    row_shift = (b.f - a.f) / a.e
    if (
        abs(col_shift - round(col_shift)) > _TOLERANCE
        or abs(row_shift - round(row_shift)) > _TOLERANCE
    ):
        raise ProcessingError(
            "sources are offset by a fraction of a pixel; resampling is not implemented"
        )
    col_shift, row_shift = round(col_shift), round(row_shift)
    if (col_shift, row_shift) == (0, 0) and before.array.shape == after.array.shape:
        return False

    col0, row0 = max(0, col_shift), max(0, row_shift)
    col1 = min(before.array.shape[1], col_shift + after.array.shape[1])
    row1 = min(before.array.shape[0], row_shift + after.array.shape[0])
    if col1 <= col0 or row1 <= row0:
        raise ProcessingError("the two observations do not overlap")
    rows, cols = row1 - row0, col1 - col0
    _crop(before, row0, col0, rows, cols)
    _crop(after, row0 - row_shift, col0 - col_shift, rows, cols)
    return True


def run(db, context) -> None:
    before, after = require_pair_loaded(context)
    align(before, after)
    # Quality is judged on the pixels both dates actually share.
    quality_control.run(db, context)
