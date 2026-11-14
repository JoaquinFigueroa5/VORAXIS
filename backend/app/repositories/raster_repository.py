from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.raster_asset import RasterAsset


class RasterRepository:
    def list_for_job(self, db: Session, job_id) -> Sequence[RasterAsset]:
        return (
            db.execute(
                select(RasterAsset)
                .where(RasterAsset.job_id == job_id)
                .order_by(RasterAsset.created_at)
            )
            .scalars()
            .all()
        )

    def list_for_observation(self, db: Session, observation_id) -> Sequence[RasterAsset]:
        return (
            db.execute(select(RasterAsset).where(RasterAsset.observation_id == observation_id))
            .scalars()
            .all()
        )

    def source_for_observation(self, db: Session, observation_id) -> RasterAsset | None:
        return db.execute(
            select(RasterAsset).where(
                RasterAsset.observation_id == observation_id,
                RasterAsset.asset_type == "SOURCE",
            )
        ).scalar_one_or_none()

    def create(
        self,
        db: Session,
        *,
        asset_type: str,
        storage_path: str,
        observation_id=None,
        job_id=None,
        format: str | None = None,
        crs: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RasterAsset:
        asset = RasterAsset(
            observation_id=observation_id,
            job_id=job_id,
            asset_type=asset_type,
            storage_path=storage_path,
            format=format,
            crs=crs,
            extra_metadata=metadata,
        )
        db.add(asset)
        db.flush()
        return asset
