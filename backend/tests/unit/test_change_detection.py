import numpy as np
import pytest

from app.core.exceptions import NotImplementedFeature
from app.processing.algorithms import gcov, require_supported
from app.processing.segmentation import clean_mask


def _pair(size: int = 60, seed: int = 42):
    rng = np.random.default_rng(seed)
    before = rng.normal(1.0, 0.05, (size, size)).astype("float32")
    after = before.copy()
    after[20:30, 25:35] += 0.8
    return before, after


def test_gcov_flags_the_injected_block():
    before, after = _pair()
    difference, flagged, score = gcov.detect(before, after, np.ones(before.shape, bool), 2.0)

    assert difference.shape == before.shape
    assert flagged[20:30, 25:35].mean() > 0.8
    assert 0.0 <= score <= 1.0


def test_gcov_flags_nothing_for_identical_rasters():
    before, _ = _pair()
    _, flagged, score = gcov.detect(before, before.copy(), np.ones(before.shape, bool), 2.0)

    assert not flagged.any()
    assert score == 0.0


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
