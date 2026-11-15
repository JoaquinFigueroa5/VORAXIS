"""Ingestion: NISAR GCOV .h5 -> COG in object storage -> Observation + RasterAsset.

    .h5 (local, or downloaded with Earthdata)
      -> crop to the location's bounding box, dB, COG   (processing/ingest_gcov.py)
      -> S3  sources/{observation_id}/{product_id}.tif
      -> catalog.observations (READY) + processing.raster_assets (SOURCE)

One SOURCE asset per observation: a single multi-band COG whose band 1 is the
co-pol channel, because the analysis pipeline reads band 1.
"""

import json
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shapely import wkt as shapely_wkt
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.integrations.nisar.asf_client import AsfClient
from app.integrations.nisar.catalog_mapper import map_asf_product
from app.integrations.nisar.earthdata_client import EarthdataClient
from app.integrations.nisar.product_name import ProductName, parse_product_name
from app.integrations.storage.minio_client import MinioStorage
from app.models.nisar_scene import NisarScene
from app.models.observation import Observation
from app.processing.ingest_gcov import GcovInfo, gcov_to_cog, inspect_gcov
from app.repositories.location_repository import LocationRepository
from app.repositories.nisar_repository import NisarRepository
from app.repositories.observation_repository import ObservationRepository
from app.repositories.raster_repository import RasterRepository
from app.utils.geometry import footprint_wkt

logger = get_logger(__name__)

SUPPORTED_PRODUCT = "GCOV"
_FRACTION = re.compile(r"\.\d+")


@dataclass
class IngestResult:
    observation_id: Any
    scene_id: Any
    asset_id: Any
    product_id: str
    storage_path: str
    crs: str | None
    skipped: bool = False  # True when a READY observation already existed
    bands: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": str(self.observation_id),
            "scene_id": str(self.scene_id),
            "asset_id": str(self.asset_id),
            "product_id": self.product_id,
            "storage_path": self.storage_path,
            "crs": self.crs,
            "skipped": self.skipped,
            "bands": self.bands,
        }


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    # NISAR writes nanoseconds; fromisoformat stops at microseconds.
    text = _FRACTION.sub(lambda m: m.group(0)[:7], value.strip().replace("Z", "+00:00"))
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class IngestService:
    def __init__(
        self,
        scenes: NisarRepository | None = None,
        observations: ObservationRepository | None = None,
        rasters: RasterRepository | None = None,
        locations: LocationRepository | None = None,
        earthdata: EarthdataClient | None = None,
        storage: MinioStorage | None = None,
        asf: AsfClient | None = None,
    ) -> None:
        self.scenes = scenes or NisarRepository()
        self.observations = observations or ObservationRepository()
        self.rasters = rasters or RasterRepository()
        self.locations = locations or LocationRepository()
        self.earthdata = earthdata or EarthdataClient()
        self.storage = storage or MinioStorage()
        self.asf = asf or AsfClient()

    def ingest(
        self,
        db,
        *,
        location_id=None,
        location_name: str | None = None,
        h5_path: str | Path | None = None,
        scene_id=None,
        product_id: str | None = None,
        polarizations: list[str] | None = None,
        frequency: str = "A",
        multilook: int = 1,
        force: bool = False,
        on_progress=None,
    ) -> IngestResult:
        """Identify the scene by `scene_id`, `product_id` or the name of `h5_path`.

        Without `h5_path` the granule is downloaded from `scene.source_url`
        (needs Earthdata credentials); a `product_id` the catalogue does not
        hold yet is looked up in ASF first. A local file missing from the
        catalogue is registered from its HDF5 metadata. Re-running is a no-op
        unless `force`. `on_progress(stage, detail)` reports DOWNLOADING,
        CONVERTING, UPLOADING and READY.
        """
        report = on_progress or (lambda stage, detail=None: None)
        location, aoi = self._location(db, location_id, location_name)
        scene = self._known_scene(db, scene_id, product_id, h5_path)
        if scene is not None and scene.product_type != SUPPORTED_PRODUCT:
            raise AppError(
                f"scene {scene.product_id} is {scene.product_type}; only GCOV ingestion exists"
            )

        # Already ingested for this zone: answer before downloading gigabytes again.
        if scene is not None and not force:
            done = self._ready_source(db, scene, location.id)
            if done is not None:
                logger.info("observation %s already ingested; skipping", done[0].id)
                report("READY")
                return self._skipped(scene, *done)

        downloaded = h5_path is None
        path = Path(h5_path) if h5_path else self._download(scene, report)
        info = inspect_gcov(path, frequency=frequency)
        declared = info.identification.get("productType")
        if isinstance(declared, str) and declared and declared.upper() != SUPPORTED_PRODUCT:
            raise AppError(f"{path.name} declares productType={declared}; expected GCOV")

        name = parse_product_name(scene.product_id if scene else path.name)
        if scene is None:
            scene = self._register_scene(db, path, info, name)

        observation = self._observation(db, scene, location.id, info, name)
        existing = self.rasters.source_for_observation(db, observation.id)
        if existing is not None and observation.storage_status == "READY" and not force:
            logger.info("observation %s already ingested; skipping", observation.id)
            self._discard(path, downloaded)
            report("READY")
            return self._skipped(scene, observation, existing)

        key = f"sources/{observation.id}/{scene.product_id}.tif"
        try:
            with tempfile.TemporaryDirectory(prefix="ingest-") as workdir:
                report("CONVERTING")
                cog = gcov_to_cog(
                    path,
                    Path(workdir) / "source.tif",
                    aoi=aoi,
                    polarizations=polarizations,
                    frequency=frequency,
                    multilook=multilook,
                )
                report("UPLOADING")
                self.storage.ensure_bucket()
                self.storage.upload_file(cog.path, key, content_type="image/tiff")

            metadata = {
                "bucket": settings.minio_bucket,
                "product_id": scene.product_id,
                "source_file": path.name,
                "sar_band": info.band,
                "frequency": info.frequency,
                "hdf5_grid": info.grid_path,
                "source_posting": [info.x_spacing, info.y_spacing],
                "polarizations": [band["polarization"] for band in cog.bands],
                **cog.as_metadata(),
            }
            if name is not None:
                metadata.update(
                    track=name.track, frame=name.frame, cycle=name.cycle, crid=name.crid
                )
            if existing is not None:
                # A new row (new id) rather than an update: caches keyed by asset id,
                # like the tile cache, must not serve the previous raster.
                self.rasters.delete(db, existing)
            existing = self.rasters.create(
                db,
                asset_type="SOURCE",
                storage_path=key,
                observation_id=observation.id,
                format="COG",
                crs=cog.crs,
                metadata=metadata,
            )
            observation.storage_status = "READY"
            observation.processing_version = observation.processing_version or (
                name.crid if name else None
            )
            db.commit()
        except Exception:
            db.rollback()
            observation.storage_status = "FAILED"
            db.add(observation)
            db.commit()
            logger.exception("ingestion of %s failed", scene.product_id)
            raise

        logger.info("ingested %s for %s -> %s", scene.product_id, location.name, key)
        self._discard(path, downloaded)
        report("READY")
        return IngestResult(
            observation_id=observation.id,
            scene_id=scene.id,
            asset_id=existing.id,
            product_id=scene.product_id,
            storage_path=key,
            crs=cog.crs,
            bands=cog.bands,
        )

    def _ready_source(self, db, scene: NisarScene, location_id):
        """(observation, SOURCE asset) when this scene is already READY for the zone."""
        found = self.observations.list(db, scene_id=scene.id, location_id=location_id, limit=1)
        if not found or found[0].storage_status != "READY":
            return None
        asset = self.rasters.source_for_observation(db, found[0].id)
        return (found[0], asset) if asset is not None else None

    @staticmethod
    def _skipped(scene: NisarScene, observation, asset) -> IngestResult:
        return IngestResult(
            observation_id=observation.id,
            scene_id=scene.id,
            asset_id=asset.id,
            product_id=scene.product_id,
            storage_path=asset.storage_path,
            crs=asset.crs,
            skipped=True,
            bands=(asset.extra_metadata or {}).get("bands", []),
        )

    @staticmethod
    def _discard(path: Path, downloaded: bool) -> None:
        """Drop a granule this run downloaded once its COG is stored, unless told to keep it.

        Only files fetched into `nisar_data_dir` go: a path the caller passed is theirs.
        A failed run keeps the file so a retry does not download it again.
        """
        if not downloaded or settings.keep_downloaded_granules:
            return
        try:
            size_gb = path.stat().st_size / 1e9
            path.unlink()
            logger.info("deleted %s (%.2f GB) after ingestion", path.name, size_gb)
        except FileNotFoundError:
            pass
        except OSError:
            logger.warning("could not delete %s", path, exc_info=True)

    def _location(self, db, location_id, location_name) -> tuple[Any, BaseGeometry]:
        if location_id is None and location_name:
            model = self.locations.get_model_by_name(db, location_name)
            if model is None:
                raise NotFoundError(f"location '{location_name}' not found")
            location_id = model.id
        if location_id is None:
            raise AppError("a location id or name is required")
        row = self.locations.get(db, location_id)
        if row is None:
            raise NotFoundError(f"location {location_id} not found")
        location, geojson = row
        return location, shape(json.loads(geojson))

    def _known_scene(self, db, scene_id, product_id, h5_path) -> NisarScene | None:
        if scene_id is not None:
            scene = db.get(NisarScene, scene_id)
            if scene is None:
                raise NotFoundError(f"scene {scene_id} not found")
            return scene
        if product_id:
            scene = self.scenes.get_by_product_id(db, product_id)
            if scene is None and h5_path is None:
                scene = self._from_asf(db, product_id)
            return scene
        if h5_path is None:
            raise AppError("pass a scene id, a product id or an .h5 file")
        return self.scenes.get_by_product_id(db, Path(h5_path).stem)

    def _from_asf(self, db, product_id: str) -> NisarScene:
        """A product the local catalogue has not synced yet: ask ASF for it by name."""
        try:
            product = self.asf.find_product(product_id)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(f"could not look up {product_id} in ASF: {str(exc)[:200]}") from exc
        payload = map_asf_product(product) if product else None
        if payload is None:
            raise NotFoundError(
                f"scene {product_id} is not in the catalogue and ASF does not list it; "
                "check the name or pass the .h5 file"
            )
        logger.info("registering scene %s from ASF", product_id)
        return self.scenes.upsert(db, **payload)

    def _download(self, scene: NisarScene | None, report=None) -> Path:
        if scene is None:  # unreachable through `ingest`, kept for direct callers
            raise AppError("cannot download without a catalogued scene")
        destination = Path(settings.nisar_data_dir) / f"{scene.product_id}.h5"
        if destination.is_file():
            logger.info("using cached granule %s", destination)
            return destination
        if not scene.source_url:
            raise AppError(f"scene {scene.product_id} has no source_url to download from")
        logger.info("downloading %s", scene.source_url)
        progress = None
        if report is not None:
            report("DOWNLOADING", {"bytes": 0, "total": None})

            def progress(done: int, total: int | None) -> None:
                report("DOWNLOADING", {"bytes": done, "total": total})

        if not self.earthdata.download(scene.source_url, destination, progress=progress):
            raise AppError(
                "Earthdata download is unavailable: set EARTHDATA_USERNAME/EARTHDATA_PASSWORD "
                f"in .env, or place the file at {destination} and pass it explicitly"
            )
        return destination

    def _register_scene(
        self, db, path: Path, info: GcovInfo, name: ProductName | None
    ) -> NisarScene:
        ident = info.identification
        start = _parse_time(ident.get("zeroDopplerStartTime")) or (name.start if name else None)
        if start is None:
            raise AppError(
                f"cannot tell when {path.name} was acquired: no zeroDopplerStartTime "
                "in the file and the name is not a NISAR granule name"
            )
        direction = ident.get("orbitPassDirection")
        logger.info("registering scene %s from the HDF5 metadata", path.stem)
        return self.scenes.upsert(
            db,
            product_id=path.stem,
            product_type=SUPPORTED_PRODUCT,
            maturity=None,
            acquisition_start=start,
            acquisition_end=_parse_time(ident.get("zeroDopplerEndTime"))
            or (name.end if name else None),
            orbit_direction=(
                str(direction).upper() if direction else (name.orbit_direction if name else None)
            ),
            polarization=info.polarizations,
            footprint_wkt=footprint_wkt(shapely_wkt.loads(info.footprint_wkt)),
            metadata={
                "origin": "local_file",
                "identification": {k: v for k, v in ident.items() if k != "boundingPolygon"},
                **({"name": name.as_metadata()} if name else {}),
            },
            source_url=None,
        )

    def _observation(
        self, db, scene: NisarScene, location_id, info: GcovInfo, name: ProductName | None
    ) -> Observation:
        found = self.observations.list(db, scene_id=scene.id, location_id=location_id, limit=1)
        if found:
            return found[0]
        version = (name.crid if name else None) or info.identification.get("productVersion")
        return self.observations.create(
            db,
            scene_id=scene.id,
            location_id=location_id,
            acquisition_date=scene.acquisition_start,
            processing_version=str(version) if version else None,
        )
