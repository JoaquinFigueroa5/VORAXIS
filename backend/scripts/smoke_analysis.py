"""Create a synthetic GCOV pair and register it in PostGIS + object storage.

Development helper: NISAR products are not reachable without Earthdata
credentials, so this builds the smallest pair that the real pipeline accepts.

    docker compose exec backend python scripts/smoke_analysis.py
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import mkdtemp

import numpy as np
import rasterio
from rasterio.transform import from_origin
from sqlalchemy import func

from app.core.database import SessionLocal
from app.core.storage import ensure_bucket, upload_file
from app.models.auxiliary_event import AuxiliaryEvent
from app.models.nisar_scene import NisarScene
from app.models.observation import Observation
from app.repositories.location_repository import LocationRepository
from app.repositories.raster_repository import RasterRepository

LOCATION_NAME = "Petén"
SIZE = 200
TRANSFORM = from_origin(780_000, 1_850_000, 30, 30)  # UTM 15N, inside the AOI
FOOTPRINT = "MULTIPOLYGON(((-90.62 15.92, -88.98 15.92, -88.98 17.82, -90.62 17.82, -90.62 15.92)))"


def _write(path: Path, array: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=SIZE,
        width=SIZE,
        count=1,
        dtype="float32",
        crs="EPSG:32615",
        transform=TRANSFORM,
        nodata=-9999.0,
        tiled=True,
        blockxsize=128,
        blockysize=128,
    ) as destination:
        destination.write(array, 1)


def _scene(db, product_id: str, start: datetime) -> NisarScene:
    scene = db.query(NisarScene).filter_by(product_id=product_id).one_or_none()
    if scene is None:
        scene = NisarScene(
            product_id=product_id,
            product_type="GCOV",
            maturity="PROVISIONAL",
            acquisition_start=start,
            acquisition_end=start + timedelta(minutes=5),
            orbit_direction="ASCENDING",
            polarization=["VV"],
            footprint=func.ST_GeomFromText(FOOTPRINT, 4326),
            source_url="https://example.invalid/synthetic.h5",
        )
        db.add(scene)
        db.commit()
    return scene


def _observation(db, scene: NisarScene, location_id, start: datetime) -> Observation:
    observation = (
        db.query(Observation)
        .filter_by(scene_id=scene.id, location_id=location_id)
        .one_or_none()
    )
    if observation is None:
        observation = Observation(
            scene_id=scene.id,
            location_id=location_id,
            acquisition_date=start,
            processing_version="synthetic-001",
            storage_status="READY",
        )
        db.add(observation)
        db.commit()
    return observation


def main() -> None:
    ensure_bucket()
    workdir = Path(mkdtemp(prefix="smoke-"))
    rng = np.random.default_rng(11)
    before = rng.normal(1.0, 0.05, (SIZE, SIZE)).astype("float32")
    after = before.copy()
    after[70:120, 60:130] += 1.2  # ~0.09 km² of "change"

    _write(workdir / "before.tif", before)
    _write(workdir / "after.tif", after)

    rasters = RasterRepository()
    with SessionLocal() as db:
        location = LocationRepository().get_model_by_name(db, LOCATION_NAME)
        if location is None:
            raise SystemExit(f"run scripts/seed_locations.py first: {LOCATION_NAME} not found")

        first = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
        second = first + timedelta(days=30)
        before_obs = _observation(
            db, _scene(db, "SMOKE_GCOV_BEFORE", first), location.id, first
        )
        after_obs = _observation(
            db, _scene(db, "SMOKE_GCOV_AFTER", second), location.id, second
        )

        for observation, name in ((before_obs, "before"), (after_obs, "after")):
            key = f"sources/{observation.id}/{name}.tif"
            upload_file(workdir / f"{name}.tif", key, content_type="image/tiff")
            if rasters.source_for_observation(db, observation.id) is None:
                rasters.create(
                    db,
                    asset_type="SOURCE",
                    storage_path=key,
                    observation_id=observation.id,
                    format="COG",
                    crs="EPSG:32615",
                )

        if not db.query(AuxiliaryEvent).filter_by(external_id="SMOKE-USGS-1").first():
            db.add(
                AuxiliaryEvent(
                    source="USGS",
                    external_id="SMOKE-USGS-1",
                    event_type="EARTHQUAKE",
                    event_date=second + timedelta(hours=6),
                    geometry=func.ST_GeomFromText("POINT(-90.2 16.75)", 4326),
                    magnitude=4.6,
                )
            )
        db.commit()

        print(f"location_id: {location.id}")
        print(f"before_observation_id: {before_obs.id}")
        print(f"after_observation_id: {after_obs.id}")


if __name__ == "__main__":
    main()
