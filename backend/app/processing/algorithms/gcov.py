"""GCOV amplitude change detection.

GCOV is Geocoded Complex COVariance: co-registered, terrain-corrected, so a
per-pixel amplitude comparison is meaningful once both scenes share a grid.
"""

import numpy as np

PRODUCT_TYPE = "GCOV"
IMPLEMENTED = True
REASON = ""


def detect(before: np.ndarray, after: np.ndarray, valid: np.ndarray, sigma_k: float):
    """Return (absolute difference, changed mask, change score).

    Threshold = k * standard deviation of the difference around its median, which
    is robust to a small changed area skewing the mean.
    """
    difference = np.abs(after.astype("float64") - before.astype("float64"))
    values = difference[valid]
    median = float(np.median(values))
    sigma = float(values.std())
    threshold = sigma_k * (sigma if sigma > 0 else 1.0)

    flagged = valid & (np.abs(difference - median) > threshold)
    if flagged.any() and threshold > 0:
        score = float(min(1.0, difference[flagged].mean() / threshold))
    else:
        score = 0.0
    return difference, flagged, score
