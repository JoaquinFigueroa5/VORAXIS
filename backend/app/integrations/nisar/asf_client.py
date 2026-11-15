"""ASF DAAC search adapter.

`asf_search` is imported lazily so the API boots (and tests run) even when the
geo/catalogue extras are not installed in the current environment.
"""

from datetime import datetime
from typing import Any

from shapely.geometry import box

from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AsfClient:
    platform = "NISAR"

    def search(
        self,
        *,
        bbox: tuple[float, float, float, float],
        start: datetime | None = None,
        end: datetime | None = None,
        max_results: int = 250,
        processing_level: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            import asf_search as asf
        except ImportError as exc:  # pragma: no cover - dependency present in the image
            raise AppError("asf_search is not installed") from exc

        kwargs: dict[str, Any] = {
            "platform": self.platform,
            "intersectsWith": box(*bbox).wkt,
            "maxResults": max_results,
        }
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end
        if processing_level:
            kwargs["processingLevel"] = processing_level

        logger.info("ASF search bbox=%s start=%s end=%s", bbox, start, end)
        results = asf.geo_search(**kwargs)
        # The footprint lives next to `properties`, not inside it; the mapper needs both.
        return [{**product.properties, "geometry": product.geometry} for product in results]

    def search_point(
        self,
        *,
        longitude: float,
        latitude: float,
        start: datetime | None = None,
        end: datetime | None = None,
        processing_level: str | None = None,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        """Products whose footprint contains the point, newest first."""
        try:
            import asf_search as asf
        except ImportError as exc:  # pragma: no cover - dependency present in the image
            raise AppError("asf_search is not installed") from exc

        kwargs: dict[str, Any] = {
            "platform": self.platform,
            "intersectsWith": f"POINT({longitude} {latitude})",
            "maxResults": max_results,
        }
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end
        if processing_level:
            kwargs["processingLevel"] = processing_level
        results = asf.search(**kwargs)
        return [{**product.properties, "geometry": product.geometry} for product in results]

    def find_product(self, product_id: str) -> dict[str, Any] | None:
        """The catalogue entry of one granule, or None when ASF does not know the name."""
        try:
            import asf_search as asf
        except ImportError as exc:  # pragma: no cover - dependency present in the image
            raise AppError("asf_search is not installed") from exc

        for product in asf.granule_search([product_id]):
            if product.properties.get("sceneName") == product_id:
                return {**product.properties, "geometry": product.geometry}
        return None
