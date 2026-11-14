from collections.abc import Sequence

from app.core.exceptions import NotFoundError, NotImplementedFeature
from app.repositories.change_repository import ChangeRepository
from app.repositories.raster_repository import RasterRepository
from app.schemas.change import ChangeEventOut, ChangeMetricOut
from app.utils.geometry import as_geojson


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
            created_at=change.created_at,
        )

    def list(self, db, **filters) -> list[ChangeEventOut]:
        return [self._to_out(row) for row in self.repo.list(db, **filters)]

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

    def tile(self, db, change_id, z: int, x: int, y: int) -> None:
        """Raster tiles are generated from COGs in MinIO (phase 5)."""
        self.get(db, change_id)
        raise NotImplementedFeature(
            "raster tiles are not generated yet; the difference COG is available as a raster asset"
        )
