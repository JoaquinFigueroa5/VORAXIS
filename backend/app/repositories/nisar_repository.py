from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.nisar_scene import NisarScene


class NisarRepository:
    def _stmt(self):
        return select(NisarScene, func.ST_AsGeoJSON(NisarScene.footprint).label("geojson"))

    def list(
        self,
        db: Session,
        *,
        product_type: str | None = None,
        maturity: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Any]:
        stmt = self._stmt()
        if product_type:
            stmt = stmt.where(NisarScene.product_type == product_type.upper())
        if maturity:
            stmt = stmt.where(NisarScene.maturity == maturity.upper())
        if start:
            stmt = stmt.where(NisarScene.acquisition_start >= start)
        if end:
            stmt = stmt.where(NisarScene.acquisition_start <= end)
        if bbox:
            stmt = stmt.where(
                func.ST_Intersects(
                    NisarScene.footprint,
                    func.ST_MakeEnvelope(*bbox, 4326),
                )
            )
        stmt = stmt.order_by(NisarScene.acquisition_start.desc()).limit(limit).offset(offset)
        return db.execute(stmt).all()

    def get(self, db: Session, scene_id) -> Any | None:
        return db.execute(self._stmt().where(NisarScene.id == scene_id)).first()

    def get_by_product_id(self, db: Session, product_id: str) -> NisarScene | None:
        return db.execute(
            select(NisarScene).where(NisarScene.product_id == product_id)
        ).scalar_one_or_none()

    def upsert(
        self,
        db: Session,
        *,
        product_id: str,
        product_type: str,
        maturity: str | None,
        acquisition_start: datetime,
        acquisition_end: datetime | None,
        orbit_direction: str | None,
        polarization: Sequence[str] | None,
        footprint_wkt: str,
        metadata: dict[str, Any] | None,
        source_url: str | None,
    ) -> NisarScene:
        scene = self.get_by_product_id(db, product_id)
        if scene is None:
            scene = NisarScene(product_id=product_id)
            db.add(scene)
        scene.product_type = product_type
        scene.maturity = maturity
        scene.acquisition_start = acquisition_start
        scene.acquisition_end = acquisition_end
        scene.orbit_direction = orbit_direction
        scene.polarization = polarization
        scene.footprint = func.ST_GeomFromText(footprint_wkt, 4326)
        scene.extra_metadata = metadata
        scene.source_url = source_url
        db.commit()
        db.refresh(scene)
        return scene

    def count(self, db: Session) -> int:
        return db.execute(select(func.count()).select_from(NisarScene)).scalar_one()
