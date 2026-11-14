"""Binary mask cleanup: remove single-pixel noise and specks."""

import numpy as np
from scipy import ndimage

MIN_PIXELS = 4


def clean_mask(mask: np.ndarray, min_pixels: int = MIN_PIXELS) -> np.ndarray:
    if not mask.any():
        return mask
    opened = ndimage.binary_opening(mask, structure=np.ones((3, 3)), iterations=1)
    if not opened.any():
        return np.zeros_like(mask)
    labelled, count = ndimage.label(opened)
    if count == 0:
        return opened
    sizes = ndimage.sum(opened, labelled, range(1, count + 1))
    keep = np.isin(labelled, np.flatnonzero(sizes >= min_pixels) + 1)
    return keep


def run(db, context) -> None:
    """Segmentation is applied inside change_detection; kept for the documented pipeline."""
    return None
