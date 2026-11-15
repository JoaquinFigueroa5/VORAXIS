from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import Affine

from app.core.exceptions import ProcessingError
from app.processing import quality_control
from app.processing.context import JobContext, LoadedRaster


def _raster(array: np.ndarray, invalid: np.ndarray) -> LoadedRaster:
    return LoadedRaster(
        path=Path("memory.tif"),
        array=array,
        invalid=invalid,
        transform=Affine.identity(),
        crs=CRS.from_epsg(32615),
        profile={},
    )


def _context(minimum: float) -> JobContext:
    return JobContext(
        job_id=uuid4(),
        location_id=uuid4(),
        before_observation_id=uuid4(),
        after_observation_id=uuid4(),
        parameters={"minimum_valid_pixel_percentage": minimum},
        workdir=Path("."),
    )


def test_valid_percentage_counts_union_of_nodata():
    array = np.ones((10, 10), dtype="float32")
    before = _raster(array, np.zeros((10, 10), dtype=bool))
    after = _raster(array, np.zeros((10, 10), dtype=bool))
    after.invalid[:5, :] = True

    assert quality_control.valid_pixel_percentage(before, after) == pytest.approx(50.0)


def test_low_valid_percentage_stops_the_pipeline():
    array = np.ones((10, 10), dtype="float32")
    before = _raster(array, np.zeros((10, 10), dtype=bool))
    after = _raster(array, np.zeros((10, 10), dtype=bool))
    after.invalid[:8, :] = True

    context = _context(minimum=80.0)
    context.before, context.after = before, after

    with pytest.raises(ProcessingError, match="below the requested"):
        quality_control.run(None, context)


def test_padding_outside_the_frame_does_not_count_against_the_pair():
    """An AOI four times larger than the frame is still a perfectly good pair."""
    array = np.ones((10, 10), dtype="float32")
    outside = np.zeros((10, 10), dtype=bool)
    outside[:, 5:] = True  # no data on either date: beyond the swath
    outside[5:, :] = True
    before, after = _raster(array, outside.copy()), _raster(array, outside.copy())

    assert quality_control.valid_pixel_percentage(before, after) == pytest.approx(100.0)
    assert quality_control.aoi_coverage_percentage(before, after) == pytest.approx(25.0)

    context = _context(minimum=80.0)
    context.before, context.after = before, after
    quality_control.run(None, context)  # does not raise
    assert context.aoi_coverage_percentage == pytest.approx(25.0)


def test_a_pair_with_no_data_at_all_fails():
    array = np.ones((4, 4), dtype="float32")
    empty = np.ones((4, 4), dtype=bool)
    context = _context(minimum=1.0)
    context.before, context.after = _raster(array, empty), _raster(array, empty.copy())

    with pytest.raises(ProcessingError, match="below the requested"):
        quality_control.run(None, context)
