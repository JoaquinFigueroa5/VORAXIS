"""Product validation shared by ingestion and pair selection."""

from typing import Any

PRODUCT_TYPES = ("GCOV", "GUNW", "GOFF", "SME2")
MATURITIES = ("PROVISIONAL", "BETA", "VALIDATED")


def _detect_from_name(text: str) -> str | None:
    for product_type in PRODUCT_TYPES:
        if f"_{product_type}_" in text or text.endswith(f"_{product_type}"):
            return product_type
    return None


def normalize_product_type(product: dict[str, Any]) -> str:
    """Prefer the explicit field; fall back to the granule name; default UNKNOWN."""
    if product.get("productType") in PRODUCT_TYPES:
        return product["productType"]
    for key in ("fileID", "sceneName", "granuleName"):
        detected = _detect_from_name(str(product.get(key) or ""))
        if detected:
            return detected
    level = str(product.get("processingLevel") or "")
    detected = _detect_from_name(level)
    return detected or level or "UNKNOWN"


def validate_payload(payload: dict[str, Any]) -> bool:
    return bool(
        payload.get("product_id")
        and payload.get("product_type") in PRODUCT_TYPES
        and payload.get("acquisition_start")
        and payload.get("footprint_wkt")
    )


def comparable(scene_a, scene_b) -> bool:
    """Cheap structural comparison. Geometry checks live in analysis_service."""
    return (
        scene_a.product_type == scene_b.product_type
        and (scene_a.maturity or "") == (scene_b.maturity or "")
    )
