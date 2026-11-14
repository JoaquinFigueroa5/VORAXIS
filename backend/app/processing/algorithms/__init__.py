"""Algorithm registry per NISAR product type.

Only GCOV (geocoded complex covariance → amplitude) is wired. The others keep a
module so callers fail with a precise message instead of producing meaningless
numbers from the wrong product.
"""

from app.core.exceptions import NotImplementedFeature
from app.processing.algorithms import gcov, goff, gunw, sme2

REGISTRY = {module.PRODUCT_TYPE: module for module in (gcov, gunw, goff, sme2)}


def get(product_type: str | None):
    return REGISTRY.get((product_type or "").upper())


def require_supported(product_type: str | None):
    module = get(product_type)
    if module is None:
        raise NotImplementedFeature(f"no algorithm for product type {product_type!r}")
    if not module.IMPLEMENTED:
        raise NotImplementedFeature(f"{product_type}: {module.REASON}")
    return module
