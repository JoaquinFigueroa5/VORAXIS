"""Raster loading: the requested polarisation, nodata as an explicit invalid mask."""

import numpy as np
import rasterio

from app.core.exceptions import ProcessingError
from app.processing.context import LoadedRaster


def select_band(source, polarization: str | None) -> int:
    """Ingested sources describe each band (`HH`, `HV`...). Undescribed rasters use band 1."""
    described = {
        description.upper(): index
        for index, description in enumerate(source.descriptions, start=1)
        if description
    }
    if not described or not polarization:
        return 1
    index = described.get(polarization.upper())
    if index is None:
        raise ProcessingError(
            f"the source raster has no {polarization} band; available: {sorted(described)}"
        )
    return index


def load(path, polarization: str | None = None) -> LoadedRaster:
    with rasterio.open(path) as source:
        band = select_band(source, polarization)
        array = source.read(band).astype("float32")
        nodata = source.nodata
        invalid = ~np.isfinite(array)
        if nodata is not None and np.isfinite(nodata):
            invalid |= array == nodata
        return LoadedRaster(
            path=path,
            array=array,
            invalid=invalid,
            transform=source.transform,
            crs=source.crs,
            profile=dict(source.profile),
            units=source.tags().get("units", "linear"),
            band=band,
            polarization=source.descriptions[band - 1],
        )


def run(db, context) -> None:
    context.before = load(context.workdir / "before.tif", context.polarization)
    context.after = load(context.workdir / "after.tif", context.polarization)
    if not context.before.crs or not context.after.crs:
        raise ProcessingError("source rasters must declare a CRS")
    if context.before.units.lower() != context.after.units.lower():
        raise ProcessingError(
            f"sources use different units ({context.before.units} vs {context.after.units})"
        )
