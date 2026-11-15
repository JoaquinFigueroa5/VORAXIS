"""ASF product -> `catalog.nisar_scenes` mapping.

NISAR metadata keys are not guaranteed to be stable across maturities, so every
field is read defensively and a product that misses the minimum set is skipped
instead of being stored half-empty.
"""

import json
from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.integrations.nisar.product_validator import normalize_product_type, validate_payload
from app.utils.geometry import geojson_to_multipolygon_wkt

logger = get_logger(__name__)

_POLARIZATION_SPLIT = (",", "+", " ")


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _polarizations(value: Any) -> list[str] | None:
    if not value:
        return None
    if isinstance(value, list):
        return [str(v) for v in value]
    text = str(value)
    for separator in _POLARIZATION_SPLIT:
        text = text.replace(separator, ",")
    return [part for part in (p.strip() for p in text.split(",")) if part]


def map_asf_product(product: dict[str, Any]) -> dict[str, Any] | None:
    product_id = product.get("fileID") or product.get("sceneName") or product.get("granuleName")
    start = _parse_datetime(product.get("startTime"))
    geometry = product.get("geometry")
    if not product_id or start is None or not geometry:
        logger.debug("skipping ASF product without id/start/geometry: %s", product_id)
        return None

    try:
        payload = {
            "product_id": str(product_id),
            "product_type": normalize_product_type(product),
            "maturity": (product.get("maturity") or product.get("productVersion") or None),
            "acquisition_start": start,
            "acquisition_end": _parse_datetime(product.get("stopTime")),
            "orbit_direction": product.get("flightDirection"),
            "polarization": _polarizations(
                product.get("polarization") or product.get("mainBandPolarization")
            ),
            "footprint_wkt": geojson_to_multipolygon_wkt(geometry),
            "metadata": json.loads(json.dumps(product, default=str)),
            "source_url": product.get("url"),
        }
    except Exception as exc:  # a bad footprint must not abort a whole sync
        logger.warning("could not map ASF product %s: %s", product_id, exc)
        return None

    return payload if validate_payload(payload) else None
