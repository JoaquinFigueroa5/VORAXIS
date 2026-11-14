"""Raster pipeline on synthetic GeoTIFFs (no database, no object storage)."""

from uuid import uuid4

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.core.exceptions import ProcessingError
from app.processing import alignment, change_detection, preprocessing, raster_export
from app.processing.context import JobContext
from app.processing.vectorization import extract_regions, mask_to_polygons
from app.services import tile_service

ORIGIN = (500_000, 1_700_000)
PIXEL = 10


def _write(path, bands, *, origin=ORIGIN, descriptions=None, units=None, pixel=PIXEL):
    """`bands` is (count, rows, cols)."""
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=bands.shape[1],
        width=bands.shape[2],
        count=bands.shape[0],
        dtype="float32",
        crs="EPSG:32615",
        transform=from_origin(*origin, pixel, pixel),
        nodata=float("nan"),
    ) as destination:
        destination.write(bands.astype("float32"))
        if descriptions:
            destination.descriptions = descriptions
        if units:
            destination.update_tags(units=units)


def _context(workdir, **parameters) -> JobContext:
    return JobContext(
        job_id=uuid4(),
        location_id=uuid4(),
        before_observation_id=uuid4(),
        after_observation_id=uuid4(),
        parameters={"minimum_valid_pixel_percentage": 50, **parameters},
        workdir=workdir,
        product_type="GCOV",
    )


def _run(context):
    preprocessing.run(None, context)
    alignment.run(None, context)
    change_detection.run(None, context)
    return context


def _scene(rng, shape=(120, 120), mean_db=-8.0):
    return (mean_db + rng.normal(0, 0.4, shape)).astype("float32")


def test_pipeline_detects_the_changed_block(tmp_path):
    rng = np.random.default_rng(7)
    before = rng.normal(1.0, 0.05, (80, 80)).astype("float32")  # linear, undescribed band
    after = before.copy()
    after[30:50, 30:50] += 1.0
    _write(tmp_path / "before.tif", before[None])
    _write(tmp_path / "after.tif", after[None])

    context = _run(_context(tmp_path, polarization="VV"))

    assert context.valid_pixel_percentage == pytest.approx(100.0)
    assert context.change_mask[32:48, 32:48].mean() > 0.95
    assert context.changed_fraction == pytest.approx(400 / 6400, rel=0.35)
    polygons = mask_to_polygons(context)
    assert len(polygons) == 1
    assert polygons[0].bounds[0] > -180 and polygons[0].bounds[2] < 180


def test_each_polygon_gets_its_own_score_and_direction(tmp_path):
    rng = np.random.default_rng(3)
    before = _scene(rng)
    after = before + rng.normal(0, 0.2, before.shape).astype("float32")
    after[15:45, 15:45] -= 8.0  # strong drop
    after[75:105, 70:110] += 3.0  # milder rise
    _write(tmp_path / "before.tif", before[None], descriptions=("HH",), units="dB")
    _write(tmp_path / "after.tif", after[None], descriptions=("HH",), units="dB")

    context = _run(_context(tmp_path))
    regions = extract_regions(context)

    assert len(regions) == 2
    drop = next(r for r in regions if r.mean_change_db < 0)
    rise = next(r for r in regions if r.mean_change_db > 0)
    assert drop.direction == "DECREASE" and rise.direction == "INCREASE"
    assert drop.mean_change_db == pytest.approx(-8.0, abs=1.0)
    assert rise.mean_change_db == pytest.approx(3.0, abs=0.6)
    assert drop.mean_before_db == pytest.approx(-8.0, abs=0.3)
    assert drop.mean_after_db == pytest.approx(-16.0, abs=1.0)
    assert 0 < rise.score < drop.score < 1
    assert drop.area_km2 == pytest.approx(0.09, rel=0.25)
    assert rise.area_km2 == pytest.approx(0.12, rel=0.25)
    assert regions[0] is drop  # strongest first


def test_small_specks_are_dropped_by_minimum_area(tmp_path):
    rng = np.random.default_rng(5)
    before = _scene(rng)
    after = before.copy()
    after[10:16, 10:16] -= 9.0  # 3 600 m2
    after[60:100, 60:100] -= 9.0  # 160 000 m2
    _write(tmp_path / "before.tif", before[None], descriptions=("HH",), units="dB")
    _write(tmp_path / "after.tif", after[None], descriptions=("HH",), units="dB")

    assert len(extract_regions(_run(_context(tmp_path, minimum_area_km2=0.01)))) == 1
    assert len(extract_regions(_run(_context(tmp_path, minimum_area_km2=0.001)))) == 2


def test_requested_polarization_selects_the_band(tmp_path):
    rng = np.random.default_rng(9)
    hh, hv = _scene(rng), _scene(rng, mean_db=-15.0)
    hv_after = hv.copy()
    hv_after[40:80, 40:80] -= 7.0  # change only visible in HV
    _write(tmp_path / "before.tif", np.stack([hh, hv]), descriptions=("HH", "HV"), units="dB")
    _write(tmp_path / "after.tif", np.stack([hh, hv_after]), descriptions=("HH", "HV"), units="dB")

    assert _run(_context(tmp_path, polarization="HH")).change_mask.sum() == 0
    hv_context = _run(_context(tmp_path, polarization="HV"))
    assert hv_context.before.polarization == "HV" and hv_context.before.band == 2
    assert hv_context.change_mask[45:75, 45:75].mean() > 0.95

    with pytest.raises(ProcessingError, match="no VV band"):
        _run(_context(tmp_path, polarization="VV"))


def test_shifted_grids_are_cropped_to_their_intersection(tmp_path):
    rng = np.random.default_rng(11)
    full = _scene(rng, shape=(140, 140))
    before = full[:120, :120]
    after = full[10:130, 20:140].copy()  # 20 px east, 10 px south
    after[40:70, 30:60] -= 8.0
    _write(tmp_path / "before.tif", before[None], descriptions=("HH",), units="dB")
    _write(
        tmp_path / "after.tif",
        after[None],
        origin=(ORIGIN[0] + 20 * PIXEL, ORIGIN[1] - 10 * PIXEL),
        descriptions=("HH",),
        units="dB",
    )

    context = _run(_context(tmp_path))

    assert context.before.array.shape == context.after.array.shape == (110, 100)
    assert context.before.transform == context.after.transform
    assert context.before.transform.c == ORIGIN[0] + 20 * PIXEL
    assert context.before.transform.f == ORIGIN[1] - 10 * PIXEL
    (region,) = extract_regions(context)
    # Same ground everywhere except the injected block.
    assert region.mean_change_db == pytest.approx(-8.0, abs=1.0)
    assert region.area_km2 == pytest.approx(0.09, rel=0.25)


def test_incompatible_grids_are_rejected_with_a_reason(tmp_path):
    rng = np.random.default_rng(13)
    scene = _scene(rng, shape=(60, 60))
    _write(tmp_path / "before.tif", scene[None], descriptions=("HH",), units="dB")

    _write(tmp_path / "after.tif", scene[None], pixel=20, descriptions=("HH",), units="dB")
    with pytest.raises(ProcessingError, match="different resolutions"):
        _run(_context(tmp_path))

    _write(tmp_path / "after.tif", scene[None], origin=(ORIGIN[0] + 4, ORIGIN[1]), descriptions=("HH",), units="dB")
    with pytest.raises(ProcessingError, match="fraction of a pixel"):
        _run(_context(tmp_path))

    _write(tmp_path / "after.tif", scene[None], origin=(ORIGIN[0] + 5_000, ORIGIN[1]), descriptions=("HH",), units="dB")
    with pytest.raises(ProcessingError, match="do not overlap"):
        _run(_context(tmp_path))


def test_exported_rasters_are_cogs_and_render_as_tiles(tmp_path):
    rng = np.random.default_rng(17)
    before = _scene(rng, shape=(700, 700))
    after = before.copy()
    after[200:400, 200:400] -= 8.0
    before[:50, :] = np.nan
    _write(tmp_path / "before.tif", before[None], descriptions=("HH",), units="dB")
    _write(tmp_path / "after.tif", after[None], descriptions=("HH",), units="dB")
    context = _run(_context(tmp_path))

    difference = raster_export.write_cog(
        tmp_path / "difference.tif",
        context.difference,
        context.before.crs,
        context.before.transform,
        nodata=float("nan"),
        tags={"units": "dB"},
    )
    mask = raster_export.write_cog(
        tmp_path / "mask.tif",
        context.change_mask.astype("uint8"),
        context.before.crs,
        context.before.transform,
        nodata=0,
    )
    for path in (difference, mask):
        with rasterio.open(path) as cog:
            assert cog.tags(ns="IMAGE_STRUCTURE")["LAYOUT"] == "COG"
            assert cog.overviews(1)
    with rasterio.open(difference) as cog:
        assert cog.tags()["units"] == "dB"
        assert np.isnan(cog.read(1)[:50, :]).all()

    # Zoom 13 tile over the raster centre.
    from rasterio.warp import transform as warp_transform

    centre_x, centre_y = ORIGIN[0] + 3_000, ORIGIN[1] - 3_000
    (mx,), (my,) = warp_transform("EPSG:32615", "EPSG:3857", [centre_x], [centre_y])
    z = 13
    size = 2 * tile_service._ORIGIN / 2**z
    x = int((mx + tile_service._ORIGIN) // size)
    y = int((tile_service._ORIGIN - my) // size)

    values = tile_service.read_tile(difference, 1, z, x, y)
    assert values.shape == (256, 256)
    rgba = tile_service.render_difference(values, context.baseline_db, context.threshold_db)
    changed = values < -4
    assert changed.any()
    assert (rgba[3][changed] > 150).all()  # the drop is drawn...
    assert (rgba[0][changed] > rgba[2][changed]).all()  # ...in red
    stable = np.isfinite(values) & (np.abs(values) < 0.3)
    assert (rgba[3][stable] == 0).all()  # stable ground is transparent

    mask_rgba = tile_service.render_mask(tile_service.read_tile(mask, 1, z, x, y, nearest=True))
    assert mask_rgba[3].max() == 200 and mask_rgba[3].min() == 0

    grey = tile_service.render_backscatter(tile_service.read_tile(tmp_path / "after.tif", 1, z, x, y), "HH")
    assert grey[0].max() > grey[0].min()

    png = tile_service._png(rgba)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    with rasterio.io.MemoryFile(png) as memory, memory.open() as image:
        assert (image.count, image.width, image.height) == (4, 256, 256)

    assert tile_service.read_tile(difference, 1, z, x + 50, y) is None  # far away: no data


def test_tile_bounds_cover_the_world_at_zoom_zero():
    left, bottom, right, top = tile_service.tile_bounds(0, 0, 0)
    assert left == -right and bottom == -top
    assert tile_service.tile_bounds(1, 1, 1)[0] == 0 and tile_service.tile_bounds(1, 1, 1)[3] == 0
