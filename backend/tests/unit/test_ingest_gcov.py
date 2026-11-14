"""HDF5 -> COG conversion on a synthetic GCOV file (no database, no MinIO)."""

from datetime import UTC, datetime

import h5py
import numpy as np
import pytest
import rasterio
from rasterio.warp import transform_bounds
from shapely.geometry import box

from app.core.exceptions import ProcessingError
from app.integrations.nisar.product_name import parse_product_name
from app.processing import alignment, preprocessing
from app.processing.context import JobContext
from app.processing.ingest_gcov import gcov_to_cog, inspect_gcov, normalize_term
from scripts.make_synthetic_gcov import DEFAULT_EPSG, DEFAULT_ORIGIN, product_name, write_gcov

START = datetime(2026, 10, 30, 23, 40, 59, tzinfo=UTC)
SHAPE = (400, 500)
POSTING = 20.0


def _aoi(minx, miny, maxx, maxy):
    """AOI in EPSG:4326 from a box expressed in the product CRS."""
    return box(*transform_bounds(f"EPSG:{DEFAULT_EPSG}", "EPSG:4326", minx, miny, maxx, maxy))


@pytest.fixture()
def granule(tmp_path):
    return write_gcov(tmp_path / f"{product_name(START, 34)}.h5", start=START, shape=SHAPE)


def test_inspect_reads_grid_and_identification(granule):
    info = inspect_gcov(granule)

    assert info.band == "LSAR"
    assert info.epsg == DEFAULT_EPSG
    assert (info.height, info.width) == SHAPE
    assert info.x_spacing == info.y_spacing == POSTING
    assert info.terms == ["HHHH", "HVHV"]
    assert info.bounds == pytest.approx(
        (DEFAULT_ORIGIN[0], DEFAULT_ORIGIN[1] - 400 * 20, DEFAULT_ORIGIN[0] + 500 * 20, DEFAULT_ORIGIN[1])
    )
    assert info.identification["productType"] == "GCOV"
    assert info.footprint_wkt.startswith("POLYGON")


def test_whole_frame_becomes_a_real_cog_in_db(granule, tmp_path):
    result = gcov_to_cog(granule, tmp_path / "out.tif")

    with h5py.File(granule) as h5:
        hh = h5["/science/LSAR/GCOV/grids/frequencyA/HHHH"][()]
    with rasterio.open(result.path) as cog:
        assert cog.tags(ns="IMAGE_STRUCTURE")["LAYOUT"] == "COG"
        assert cog.count == 2
        assert cog.descriptions == ("HH", "HV")
        assert cog.crs.to_epsg() == DEFAULT_EPSG
        assert (cog.height, cog.width) == SHAPE
        assert cog.transform.c == DEFAULT_ORIGIN[0] and cog.transform.f == DEFAULT_ORIGIN[1]
        assert np.isnan(cog.nodata)
        np.testing.assert_allclose(cog.read(1), 10 * np.log10(hh), rtol=1e-5)

    assert result.frame_coverage == 1.0
    assert result.bands[0]["valid_fraction"] == 1.0
    assert -12 < result.bands[0]["mean_db"] < -5
    assert result.bands[1]["mean_db"] < result.bands[0]["mean_db"]


def test_aoi_inside_the_frame_is_cropped_on_the_source_grid(granule, tmp_path):
    x0, y0 = DEFAULT_ORIGIN
    aoi = _aoi(x0 + 2_000, y0 - 5_000, x0 + 6_000, y0 - 1_000)

    result = gcov_to_cog(granule, tmp_path / "out.tif", aoi=aoi, polarizations=["HH"])

    with h5py.File(granule) as h5:
        hh = h5["/science/LSAR/GCOV/grids/frequencyA/HHHH"][()]
    with rasterio.open(result.path) as cog:
        assert cog.count == 1
        # Pixel edges stay on the 20 m lattice of the product.
        col = (cog.transform.c - x0) / POSTING
        row = (y0 - cog.transform.f) / POSTING
        assert col == int(col) and row == int(row)
        assert 95 <= col <= 100 and 45 <= row <= 50
        assert 200 <= cog.width <= 210 and 200 <= cog.height <= 210
        window = hh[int(row) : int(row) + cog.height, int(col) : int(col) + cog.width]
        np.testing.assert_allclose(cog.read(1), 10 * np.log10(window), rtol=1e-5)


def test_aoi_larger_than_the_frame_is_padded_with_nodata(granule, tmp_path):
    x0, y0 = DEFAULT_ORIGIN
    aoi = _aoi(x0 - 3_000, y0 - 4_000, x0 + 4_000, y0 + 2_000)

    result = gcov_to_cog(granule, tmp_path / "out.tif", aoi=aoi)

    assert 0 < result.frame_coverage < 1
    with rasterio.open(result.path) as cog:
        data = cog.read(1)
        assert cog.transform.c < x0 and cog.transform.f > y0
    assert np.isnan(data[0, 0])  # north-west of the frame
    assert np.isfinite(data[-1, -1])
    assert result.bands[0]["valid_fraction"] == pytest.approx(result.frame_coverage, abs=0.01)


def test_two_dates_of_one_aoi_share_a_grid_the_pipeline_accepts(tmp_path):
    """Frames shifted by whole pixels must still align after ingestion."""
    x0, y0 = DEFAULT_ORIGIN
    before = write_gcov(tmp_path / "before.h5", start=START, shape=SHAPE)
    after = write_gcov(
        tmp_path / "after.h5",
        start=START,
        shape=SHAPE,
        origin=(x0 - 200, y0 + 100),
        seed=12,
    )
    aoi = _aoi(x0 + 1_000, y0 - 6_000, x0 + 7_000, y0 - 1_000)

    gcov_to_cog(before, tmp_path / "before.tif", aoi=aoi, polarizations=["HH"])
    gcov_to_cog(after, tmp_path / "after.tif", aoi=aoi, polarizations=["HH"])

    from uuid import uuid4

    context = JobContext(
        job_id=uuid4(),
        location_id=uuid4(),
        before_observation_id=uuid4(),
        after_observation_id=uuid4(),
        parameters={},
        workdir=tmp_path,
        product_type="GCOV",
    )
    preprocessing.run(None, context)
    alignment.run(None, context)  # raises if the grids differ
    assert context.valid_pixel_percentage == pytest.approx(100.0)


def test_multilook_averages_power_not_decibels(granule, tmp_path):
    result = gcov_to_cog(granule, tmp_path / "out.tif", multilook=4, polarizations=["HHHH"])

    with h5py.File(granule) as h5:
        hh = h5["/science/LSAR/GCOV/grids/frequencyA/HHHH"][()]
    expected = 10 * np.log10(hh.reshape(100, 4, 125, 4).mean(axis=(1, 3)))
    with rasterio.open(result.path) as cog:
        assert (cog.height, cog.width) == (100, 125)
        assert cog.res == (80.0, 80.0)
        np.testing.assert_allclose(cog.read(1), expected, rtol=1e-4)
    assert result.multilook == 4


def test_invalid_pixels_become_nodata(tmp_path):
    hole = (slice(10, 30), slice(40, 80))
    granule = write_gcov(tmp_path / "holes.h5", start=START, shape=SHAPE, nodata_block=hole)
    with h5py.File(granule, "r+") as h5:
        h5["/science/LSAR/GCOV/grids/frequencyA/HHHH"][100, 100] = 0.0
        h5["/science/LSAR/GCOV/grids/frequencyA/HHHH"][101, 100] = -1.0

    result = gcov_to_cog(granule, tmp_path / "out.tif", polarizations=["HH"])

    with rasterio.open(result.path) as cog:
        data = cog.read(1)
    assert np.isnan(data[hole]).all()
    assert np.isnan(data[100, 100]) and np.isnan(data[101, 100])
    assert np.isfinite(data).sum() == data.size - 20 * 40 - 2


def test_aoi_outside_the_frame_is_rejected(granule, tmp_path):
    with pytest.raises(ProcessingError, match="does not overlap"):
        gcov_to_cog(granule, tmp_path / "out.tif", aoi=box(-70.7, -33.3, -70.0, -32.5))
    assert not list(tmp_path.glob("*.tif"))


def test_unknown_polarization_is_rejected(granule, tmp_path):
    with pytest.raises(ProcessingError, match="available terms"):
        gcov_to_cog(granule, tmp_path / "out.tif", polarizations=["VV"])
    with pytest.raises(ProcessingError, match="not a backscatter term"):
        normalize_term("HHHV")


def test_missing_layout_gives_an_actionable_error(tmp_path):
    path = tmp_path / "other.h5"
    with h5py.File(path, "w") as h5:
        h5.create_group("/science/LSAR/RSLC")
    with pytest.raises(ProcessingError, match="no GCOV grid found"):
        inspect_gcov(path)


def test_product_name_fields():
    name = parse_product_name(
        "NISAR_L2_PR_GCOV_035_098_A_019_2005_DHDH_M_20261111T234059_20261111T234134_P05036_N_F_J_001.h5"
    )
    assert name.product_type == "GCOV"
    assert (name.cycle, name.track, name.frame) == (35, 98, 19)
    assert name.orbit_direction == "ASCENDING"
    assert name.crid == "P05036"
    assert name.start == datetime(2026, 11, 11, 23, 40, 59, tzinfo=UTC)
    assert parse_product_name("SMOKE_GCOV_BEFORE") is None
