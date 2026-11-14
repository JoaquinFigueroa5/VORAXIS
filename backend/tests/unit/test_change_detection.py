import numpy as np
import pytest

from app.core.exceptions import NotImplementedFeature
from app.processing.algorithms import gcov, require_supported
from app.processing.segmentation import clean_mask


def _speckled(size: int = 120, seed: int = 42, looks: int = 16):
    """Two independent looks at the same -8 dB scene (linear power)."""
    rng = np.random.default_rng(seed)
    truth = np.full((size, size), 10 ** (-8 / 10))
    before = truth * rng.gamma(looks, 1 / looks, truth.shape)
    after = truth * rng.gamma(looks, 1 / looks, truth.shape)
    return before.astype("float32"), after.astype("float32")


def test_log_ratio_is_signed_and_in_db():
    before = np.full((40, 40), 0.2, dtype="float32")
    after = before.copy()
    after[5:15, 5:15] *= 10 ** (-6 / 10)  # darker: flood / burn scar
    after[25:35, 25:35] *= 10 ** (4 / 10)  # brighter

    difference, flagged, threshold, baseline = gcov.detect(
        before, after, np.ones(before.shape, bool), 2.0, smoothing_window=1
    )

    assert difference[10, 10] == pytest.approx(-6.0, abs=1e-3)
    assert difference[30, 30] == pytest.approx(4.0, abs=1e-3)
    assert baseline == pytest.approx(0.0, abs=1e-6)
    assert threshold == gcov.MINIMUM_THRESHOLD_DB
    assert flagged[5:15, 5:15].all() and flagged[25:35, 25:35].all()
    assert flagged.sum() == 200


def test_db_sources_are_not_converted_twice():
    before = np.full((20, 20), -8.0, dtype="float32")
    after = before.copy()
    after[5:10, 5:10] = -14.0

    difference, flagged, _, _ = gcov.detect(
        before, after, np.ones(before.shape, bool), 2.0, units="dB", smoothing_window=1
    )

    assert difference[7, 7] == pytest.approx(-6.0)
    assert flagged.sum() == 25


def test_speckle_alone_is_mostly_not_change():
    before, after = _speckled()
    _, flagged, threshold, _ = gcov.detect(before, after, np.ones(before.shape, bool), 3.0)

    assert threshold >= gcov.MINIMUM_THRESHOLD_DB
    assert clean_mask(flagged).mean() < 0.01


def test_a_real_drop_is_found_inside_speckle():
    before, after = _speckled()
    after[40:70, 30:80] *= 10 ** (-5 / 10)

    _, flagged, _, _ = gcov.detect(before, after, np.ones(before.shape, bool), 3.0)
    flagged = clean_mask(flagged)

    assert flagged[42:68, 32:78].mean() > 0.95
    outside = flagged.copy()
    outside[36:74, 26:84] = False
    assert outside.mean() < 0.01


def test_scene_wide_offset_is_a_baseline_not_a_change():
    before, after = _speckled()
    after *= 10 ** (1.5 / 10)  # e.g. wetter soil everywhere

    _, flagged, _, baseline = gcov.detect(before, after, np.ones(before.shape, bool), 3.0)

    assert baseline == pytest.approx(1.5, abs=0.1)
    assert clean_mask(flagged).mean() < 0.01


def test_a_large_change_does_not_inflate_the_threshold():
    """MAD, unlike a standard deviation, ignores a changed third of the scene."""
    before, after = _speckled()
    quiet = gcov.detect(before, after, np.ones(before.shape, bool), 3.0)[2]
    after[:40, :] *= 10 ** (-8 / 10)
    busy = gcov.detect(before, after, np.ones(before.shape, bool), 3.0)[2]

    assert busy < quiet * 2.5


def test_invalid_pixels_stay_out_of_the_result():
    before, after = _speckled(size=40)
    valid = np.ones(before.shape, bool)
    valid[:10, :] = False
    after[:10, :] *= 100

    difference, flagged, _, _ = gcov.detect(before, after, valid, 3.0)

    assert np.isnan(difference[:10, :]).all()
    assert not flagged[:10, :].any()


def test_pixels_dark_on_both_dates_are_ignored_but_a_flood_is_kept():
    before = np.full((60, 60), -9.0, dtype="float32")
    after = before.copy()
    before[:20, :], after[:20, :] = -38.0, -33.0  # open water, wind changed: noise
    after[30:50, 10:40] = -34.0  # land that went dark: a flood

    _, flagged, _, _ = gcov.detect(
        before, after, np.ones(before.shape, bool), 3.0,
        units="dB", smoothing_window=1, noise_floor_db=-30.0,
    )

    assert not flagged[:20, :].any()
    assert flagged[30:50, 10:40].all()


def test_swath_rim_is_ignored_but_the_raster_border_is_not():
    before = np.full((80, 80), -9.0, dtype="float32")
    after = before.copy()
    valid = np.ones(before.shape, bool)
    valid[:, :20] = False  # outside the swath
    after[:, 20:24] = -3.0  # fading rim that differs between dates
    after[30:50, 70:80] = -15.0  # real change touching the raster border

    _, flagged, _, _ = gcov.detect(
        before, after, valid, 3.0, units="dB", smoothing_window=1, edge_buffer_pixels=6
    )

    assert not flagged[:, :26].any()
    assert flagged[30:50, 70:80].all()


def test_identical_rasters_have_no_change():
    before, _ = _speckled(size=40)
    _, flagged, _, baseline = gcov.detect(before, before.copy(), np.ones(before.shape, bool), 2.0)

    assert not flagged.any()
    assert baseline == 0.0


def test_score_grows_with_the_change_and_stays_below_one():
    assert gcov.score(1.0, 2.0) == 0.0
    assert gcov.score(2.0, 2.0) == 0.0
    assert gcov.score(4.0, 2.0) == pytest.approx(0.5)
    assert gcov.score(8.0, 2.0) == pytest.approx(0.75)
    assert gcov.score(8.0, 2.0) < gcov.score(20.0, 2.0) < 1.0


def test_clean_mask_removes_single_pixel_noise():
    mask = np.zeros((20, 20), dtype=bool)
    mask[10, 10] = True
    mask[2:6, 2:6] = True

    cleaned = clean_mask(mask)

    assert not cleaned[10, 10]
    assert cleaned[2:6, 2:6].all()


def test_unimplemented_products_fail_with_a_reason():
    with pytest.raises(NotImplementedFeature, match="GUNW"):
        require_supported("GUNW")
