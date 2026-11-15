from collections.abc import Sequence
from typing import Any

from app.core.exceptions import NotFoundError
from app.evidence.classification import LABELS_ES
from app.repositories.change_repository import ChangeRepository
from app.repositories.raster_repository import RasterRepository
from app.schemas.change import ChangeEventOut, ChangeMetricOut
from app.utils.geometry import as_geojson


def tolerance_for_zoom(zoom: float | None) -> float:
    """Degrees that one screen pixel spans at a web-map zoom; 0 = keep every vertex."""
    if zoom is None:
        return 0.0
    return 360.0 / (256 * 2 ** max(0.0, min(22.0, zoom)))


class ChangeService:
    def __init__(
        self,
        repo: ChangeRepository | None = None,
        rasters: RasterRepository | None = None,
    ) -> None:
        self.repo = repo or ChangeRepository()
        self.rasters = rasters or RasterRepository()

    @staticmethod
    def _to_out(row) -> ChangeEventOut:
        change, geojson = row
        return ChangeEventOut(
            id=change.id,
            job_id=change.job_id,
            change_type=change.change_type,
            geometry=as_geojson(geojson),
            area_km2=change.area_km2,
            change_score=change.change_score,
            valid_pixel_percentage=change.valid_pixel_percentage,
            direction=change.direction,
            mean_change_db=change.mean_change_db,
            classification=change.classification,
            created_at=change.created_at,
        )

    def list(self, db, **filters) -> list[ChangeEventOut]:
        return [self._to_out(row) for row in self.repo.list(db, **filters)]

    def count(self, db, **filters) -> int:
        return self.repo.count(db, **filters)

    def geojson(
        self, db, *, zoom: float | None = None, sort: str = "area", limit: int = 2000, **filters
    ) -> dict[str, Any]:
        """A FeatureCollection ready for a map source, largest changes first by default."""
        rows = self.repo.features(
            db, tolerance_degrees=tolerance_for_zoom(zoom), sort=sort, limit=limit, **filters
        )
        features = []
        for change, geojson in rows:
            geometry = as_geojson(geojson)
            if not geometry or not geometry.get("coordinates"):
                continue  # simplified away at this zoom
            features.append(
                {
                    "type": "Feature",
                    "id": str(change.id),
                    "geometry": geometry,
                    "properties": {
                        "id": str(change.id),
                        "job_id": str(change.job_id),
                        "change_type": change.change_type,
                        "label": LABELS_ES.get(change.change_type, change.change_type),
                        "direction": change.direction,
                        "change_score": change.change_score,
                        "area_km2": change.area_km2,
                        "mean_change_db": change.mean_change_db,
                    },
                }
            )
        return {
            "type": "FeatureCollection",
            "numberMatched": self.repo.count(db, **filters),
            "numberReturned": len(features),
            "features": features,
        }

    def get(self, db, change_id) -> ChangeEventOut:
        row = self.repo.get(db, change_id)
        if row is None:
            raise NotFoundError(f"change {change_id} not found")
        return self._to_out(row)

    def metrics(self, db, change_id) -> Sequence[ChangeMetricOut]:
        self.get(db, change_id)
        return [
            ChangeMetricOut(
                id=metric.id,
                change_event_id=metric.change_event_id,
                metric_name=metric.metric_name,
                value=metric.value,
                unit=metric.unit,
                source=metric.source,
                metadata=metric.extra_metadata,
            )
            for metric in self.repo.metrics(db, change_id)
        ]
