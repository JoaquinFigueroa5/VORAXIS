"""GCOV backscatter change detection.

GCOV is geocoded, terrain-corrected backscatter, so a per-pixel comparison is
meaningful once both scenes share a grid. The change measure is the signed
log-ratio in dB:

    d = 10 * log10(after / before)        (= after_dB - before_dB)

Negative d = the surface got darker (open water after a flood, burn scars,
cleared forest); positive d = brighter (flooded vegetation, new structures,
regrowth). SAR speckle is multiplicative, which is why a ratio is used instead
of a difference.
"""

import numpy as np
from scipy import ndimage

PRODUCT_TYPE = "GCOV"
IMPLEMENTED = True
REASON = ""

# MAD -> standard deviation for a normal distribution.
MAD_TO_SIGMA = 1.4826
# Below this a "change" is within radiometric noise no matter how quiet the scene is.
MINIMUM_THRESHOLD_DB = 1.0


def to_db(array: np.ndarray, units: str) -> np.ndarray:
    values = array.astype("float32")
    if units.lower() == "db":
        return values
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(values > 0, 10.0 * np.log10(values), np.nan).astype("float32")


def smooth(values: np.ndarray, valid: np.ndarray, window: int) -> np.ndarray:
    """Median filter against speckle.

    A median keeps the edges of a changed area where they are; a boxcar mean
    bleeds the change into its surroundings and inflates every polygon.
    Invalid pixels are filled with the scene median so they cannot drag their
    neighbours, then masked out again.
    """
    if window <= 1 or not valid.any():
        return np.where(valid, values, np.nan).astype("float32")
    fill = float(np.median(values[valid]))
    filled = np.where(valid, values, fill).astype("float32")
    result = ndimage.median_filter(filled, size=window, mode="nearest")
    return np.where(valid, result, np.nan).astype("float32")


def detect(
    before: np.ndarray,
    after: np.ndarray,
    valid: np.ndarray,
    sigma_k: float,
    *,
    units: str = "linear",
    smoothing_window: int = 5,
    noise_floor_db: float | None = None,
    edge_buffer_pixels: int = 0,
):
    """Return (log-ratio dB, changed mask, threshold dB, baseline dB).

    The baseline is the median log-ratio: a scene-wide offset (calibration,
    soil moisture, season) is not a local change, so pixels are flagged by how
    far they sit from it. The spread comes from the MAD, which a changed area
    cannot inflate the way it inflates a standard deviation.
    """
    before_db, after_db = to_db(before, units), to_db(after, units)
    valid = valid & np.isfinite(before_db) & np.isfinite(after_db)
    if edge_buffer_pixels > 0:
        # The rim of a swath fades into noise and looks like change between dates.
        # `nearest` keeps the raster's own border from being treated as a rim.
        size = 2 * edge_buffer_pixels + 1
        inside = ndimage.uniform_filter(valid.astype("float32"), size=size, mode="nearest")
        valid = valid & (inside > 1.0 - 0.5 / size**2)
    if noise_floor_db is not None:
        # Dark on BOTH dates (calm water, radar shadow): the ratio of two noise
        # measurements says nothing. Dark on one date only is kept: that is a flood.
        with np.errstate(invalid="ignore"):
            valid &= (before_db > noise_floor_db) | (after_db > noise_floor_db)
    difference = smooth(after_db - before_db, valid, smoothing_window)

    values = difference[valid]
    if values.size == 0:
        return difference, np.zeros(valid.shape, dtype=bool), MINIMUM_THRESHOLD_DB, 0.0
    baseline = float(np.median(values))
    sigma = float(np.median(np.abs(values - baseline))) * MAD_TO_SIGMA
    threshold = max(sigma_k * sigma, MINIMUM_THRESHOLD_DB)

    with np.errstate(invalid="ignore"):
        flagged = valid & (np.abs(difference - baseline) > threshold)
    return difference, flagged, threshold, baseline


def score(mean_deviation_db: float, threshold_db: float) -> float:
    """Relative intensity in [0, 1): 0 at the threshold, 0.5 at twice it. Not a probability."""
    if mean_deviation_db <= 0 or threshold_db <= 0:
        return 0.0
    return float(min(1.0, max(0.0, 1.0 - threshold_db / mean_deviation_db)))
