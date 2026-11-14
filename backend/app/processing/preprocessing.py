"""Raster loading: one band, nodata as an explicit invalid mask."""

import numpy as np
import rasterio

from app.core.exceptions import ProcessingError
from app.processing import quality_control
from app.processing.context import LoadedRaster


def load(path) -> LoadedRaster:
    with rasterio.open(path) as source:
        array = source.read(1).astype("float32")
        nodata = source.nodata
        invalid = ~np.isfinite(array)
        if nodata is not None:
            invalid |= array == nodata
        return LoadedRaster(
            path=path,
            array=array,
            invalid=invalid,
            transform=source.transform,
            crs=source.crs,
            profile=dict(source.profile),
        )


def run(db, context) -> None:
    context.before = load(context.workdir / "before.tif")
    context.after = load(context.workdir / "after.tif")
    if not context.before.crs or not context.after.crs:
        raise ProcessingError("source rasters must declare a CRS")
    quality_control.run(db, context)
