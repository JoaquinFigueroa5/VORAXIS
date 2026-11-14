"""Raster pipeline arithmetic on two synthetic GeoTIFFs (no database, no MinIO)."""

from uuid import uuid4

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.processing import alignment, change_detection, preprocessing
from app.processing.context import JobContext
from app.processing.vectorization import mask_to_polygons

TRANSFORM = from_origin(500_000, 1_700_000, 10, 10)


def _write(path, array):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32615",
        transform=TRANSFORM,
        nodata=-9999.0,
    ) as destination:
        destination.write(array, 1)


@pytest.fixture()
def synthetic_pair(tmp_path):
    rng = np.random.default_rng(7)
    before = rng.normal(1.0, 0.05, (80, 80)).astype("float32")
    after = before.copy()
    after[30:50, 30:50] += 1.0
    _write(tmp_path / "before.tif", before)
    _write(tmp_path / "after.tif", after)
    return tmp_path


def test_pipeline_detects_the_changed_block(synthetic_pair):
    context = JobContext(
        job_id=uuid4(),
        location_id=uuid4(),
        before_observation_id=uuid4(),
        after_observation_id=uuid4(),
        parameters={"change_threshold_sigma": 2.0, "minimum_valid_pixel_percentage": 50},
        workdir=synthetic_pair,
        product_type="GCOV",
    )

    preprocessing.run(None, context)
    alignment.run(None, context)
    change_detection.run(None, context)

    assert context.valid_pixel_percentage == pytest.approx(100.0)
    assert context.change_mask[30:50, 30:50].mean() > 0.9
    assert context.changed_fraction == pytest.approx(400 / 6400, rel=0.2)

    polygons = mask_to_polygons(context)
    assert len(polygons) == 1
    assert polygons[0].bounds[0] > -180 and polygons[0].bounds[2] < 180
