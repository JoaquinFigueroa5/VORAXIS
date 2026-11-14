"""XYZ raster tiles (256 px PNG, Web Mercator) rendered from the COGs in object storage.

Layers of an analysis job:

    before / after   backscatter of each date, grey scale in dB
    difference       signed log-ratio: red = darker, blue = brighter, transparent = no change
    mask             pixels flagged as changed

COGs are copied once into a local cache; the internal overviews make low zoom
levels cheap to read.
"""

import math
import tempfile
import threading
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.core.storage import download_object
from app.models.processing_job import ProcessingJob
from app.models.raster_asset import RasterAsset
from app.repositories.raster_repository import RasterRepository

TILE_SIZE = 256
LAYERS = ("before", "after", "difference", "mask")
_ORIGIN = 20037508.342789244  # half the Web Mercator world, metres

# dB stretch for the grey-scale backscatter layers.
_STRETCH = {"co": (-22.0, -2.0), "cross": (-28.0, -8.0)}
_DIFFERENCE_RANGE_DB = 6.0  # full colour at +/- this many dB
_DARKER = (215, 48, 39)  # red: backscatter dropped
_BRIGHTER = (69, 117, 180)  # blue: backscatter rose
_MASK_COLOUR = (255, 140, 0, 200)

_download_lock = threading.Lock()


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """EPSG:3857 bounds (left, bottom, right, top) of an XYZ tile."""
    size = 2 * _ORIGIN / (2**z)
    left = -_ORIGIN + x * size
    top = _ORIGIN - y * size
    return left, top - size, left + size, top


def _png(rgba: np.ndarray) -> bytes:
    with MemoryFile() as memory:
        with memory.open(
            driver="PNG", height=rgba.shape[1], width=rgba.shape[2], count=4, dtype="uint8"
        ) as sink:
            sink.write(rgba)
        return memory.read()


EMPTY_TILE = _png(np.zeros((4, TILE_SIZE, TILE_SIZE), dtype="uint8"))


def render_backscatter(values: np.ndarray, polarization: str) -> np.ndarray:
    low, high = _STRETCH["co" if polarization[:1] == polarization[1:2] else "cross"]
    valid = np.isfinite(values)
    scaled = np.clip((np.where(valid, values, low) - low) / (high - low), 0.0, 1.0)
    grey = (scaled * 255).astype("uint8")
    return np.stack([grey, grey, grey, np.where(valid, 255, 0).astype("uint8")])


def render_difference(values: np.ndarray, baseline: float, threshold: float) -> np.ndarray:
    """Diverging colours; opacity grows with the change so stable ground stays see-through."""
    valid = np.isfinite(values)
    deviation = np.where(valid, values - baseline, 0.0)
    strength = np.clip(np.abs(deviation) / _DIFFERENCE_RANGE_DB, 0.0, 1.0)
    darker = deviation < 0
    rgba = np.zeros((4, *values.shape), dtype="uint8")
    for channel in range(3):
        rgba[channel] = np.where(darker, _DARKER[channel], _BRIGHTER[channel])
    # Fully transparent under half the detection threshold, opaque at the full range.
    floor = 0.5 * threshold / _DIFFERENCE_RANGE_DB
    alpha = np.clip((strength - floor) / max(1e-6, 1.0 - floor), 0.0, 1.0)
    rgba[3] = np.where(valid, (alpha**0.6 * 235), 0).astype("uint8")
    return rgba


def render_mask(values: np.ndarray) -> np.ndarray:
    changed = np.nan_to_num(values, nan=0.0) > 0
    rgba = np.zeros((4, *values.shape), dtype="uint8")
    for channel in range(4):
        rgba[channel] = np.where(changed, _MASK_COLOUR[channel], 0)
    return rgba


def read_tile(path: Path, band: int, z: int, x: int, y: int, *, nearest: bool = False):
    """Warp one band onto the tile grid. Returns None when the tile misses the raster."""
    bounds = tile_bounds(z, x, y)
    with rasterio.open(path) as source:
        west, south, east, north = transform_bounds(source.crs, "EPSG:3857", *source.bounds)
        if bounds[0] >= east or bounds[2] <= west or bounds[1] >= north or bounds[3] <= south:
            return None
        is_float = np.issubdtype(np.dtype(source.dtypes[band - 1]), np.floating)
        with WarpedVRT(
            source,
            crs="EPSG:3857",
            transform=from_bounds(*bounds, TILE_SIZE, TILE_SIZE),
            width=TILE_SIZE,
            height=TILE_SIZE,
            resampling=Resampling.nearest if nearest else Resampling.bilinear,
            src_nodata=source.nodata,
            nodata=float("nan") if is_float else 0,
        ) as vrt:
            return vrt.read(band).astype("float32")


class TileService:
    def __init__(self, rasters: RasterRepository | None = None) -> None:
        self.rasters = rasters or RasterRepository()
        self.cache_dir = Path(settings.tile_cache_dir or Path(tempfile.gettempdir()) / "voraxis-tiles")

    def _job(self, db, job_id) -> ProcessingJob:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        return job

    def _job_assets(self, db, job_id) -> dict[str, RasterAsset]:
        return {asset.asset_type: asset for asset in self.rasters.list_for_job(db, job_id)}

    def _asset(self, db, job: ProcessingJob, layer: str) -> RasterAsset:
        if layer in ("before", "after"):
            observation_id = (
                job.before_observation_id if layer == "before" else job.after_observation_id
            )
            asset = self.rasters.source_for_observation(db, observation_id)
        else:
            asset = self._job_assets(db, job.id).get("DIFFERENCE" if layer == "difference" else "MASK")
        if asset is None:
            raise NotFoundError(
                f"job {job.id} has no '{layer}' raster yet (status {job.status})"
            )
        return asset

    def _local(self, asset: RasterAsset) -> Path:
        """Object storage -> local cache, once per asset version."""
        stamp = f"{asset.id}-{abs(hash(asset.storage_path)) & 0xFFFFFFFF:08x}"
        path = self.cache_dir / f"{stamp}.tif"
        if path.is_file():
            return path
        with _download_lock:
            if not path.is_file():
                partial = path.with_suffix(".part")
                download_object(asset.storage_path, partial)
                partial.replace(path)
        return path

    def _polarization(self, db, job: ProcessingJob, requested: str | None) -> str:
        if requested:
            return requested.upper()
        difference = self._job_assets(db, job.id).get("DIFFERENCE")
        return str((difference.extra_metadata or {}).get("polarization") or "HH") if difference else "HH"

    @staticmethod
    def _band(path: Path, polarization: str) -> int:
        with rasterio.open(path) as source:
            described = {
                (name or "").upper(): index
                for index, name in enumerate(source.descriptions, start=1)
                if name
            }
        if not described:
            return 1
        if polarization not in described:
            raise AppError(f"no {polarization} band; available: {sorted(described)}")
        return described[polarization]

    def tile(
        self, db, job_id, layer: str, z: int, x: int, y: int, polarization: str | None = None
    ) -> bytes:
        layer = layer.lower()
        if layer not in LAYERS:
            raise AppError(f"layer must be one of {', '.join(LAYERS)}")
        if not (0 <= z <= 22 and 0 <= x < 2**z and 0 <= y < 2**z):
            raise AppError("tile coordinates out of range")

        job = self._job(db, job_id)
        asset = self._asset(db, job, layer)
        path = self._local(asset)

        if layer in ("before", "after"):
            polarization = self._polarization(db, job, polarization)
            values = read_tile(path, self._band(path, polarization), z, x, y)
            return EMPTY_TILE if values is None else _png(render_backscatter(values, polarization))
        if layer == "difference":
            values = read_tile(path, 1, z, x, y)
            if values is None:
                return EMPTY_TILE
            metadata = asset.extra_metadata or {}
            return _png(
                render_difference(
                    values,
                    float(metadata.get("baseline_db") or 0.0),
                    float(metadata.get("threshold_db") or 1.0),
                )
            )
        values = read_tile(path, 1, z, x, y, nearest=True)
        return EMPTY_TILE if values is None else _png(render_mask(values))

    def describe(self, db, job_id, base_path: str) -> dict[str, Any]:
        """What the map needs to add the layers: URL templates, bounds, zoom range, legend."""
        job = self._job(db, job_id)
        assets = self._job_assets(db, job.id)
        difference = assets.get("DIFFERENCE")
        available = [layer for layer in LAYERS if self._has(db, job, layer, assets)]
        bounds = None
        maxzoom = 14
        reference = difference or self.rasters.source_for_observation(db, job.before_observation_id)
        if reference is not None:
            with rasterio.open(self._local(reference)) as source:
                bounds = [round(v, 6) for v in transform_bounds(source.crs, "EPSG:4326", *source.bounds)]
                # Native zoom: where a tile pixel is about one raster pixel.
                latitude = math.radians((bounds[1] + bounds[3]) / 2)
                metres = 2 * _ORIGIN * math.cos(latitude) / TILE_SIZE
                maxzoom = max(1, min(18, math.ceil(math.log2(metres / abs(source.res[0])))))
        metadata = (difference.extra_metadata or {}) if difference else {}
        polarization = str(metadata.get("polarization") or "HH")
        low, high = _STRETCH["co" if polarization[:1] == polarization[1:2] else "cross"]
        return {
            "job_id": str(job.id),
            "status": job.status,
            "tile_size": TILE_SIZE,
            "scheme": "xyz",
            "bounds": bounds,
            "minzoom": 0,
            "maxzoom": maxzoom,
            "polarization": polarization,
            "layers": {
                layer: f"{base_path}/{{z}}/{{x}}/{{y}}?layer={layer}" for layer in available
            },
            "legend": {
                "before": {"units": "dB", "min": low, "max": high, "palette": "grey"},
                "after": {"units": "dB", "min": low, "max": high, "palette": "grey"},
                "difference": {
                    "units": "dB",
                    "min": -_DIFFERENCE_RANGE_DB,
                    "max": _DIFFERENCE_RANGE_DB,
                    "negative": "#d73027",
                    "positive": "#4575b4",
                    "threshold_db": metadata.get("threshold_db"),
                    "baseline_db": metadata.get("baseline_db"),
                    "meaning": {
                        "negative": "backscatter dropped (darker surface)",
                        "positive": "backscatter rose (brighter surface)",
                    },
                },
                "mask": {"colour": "#ff8c00"},
            },
        }

    def _has(self, db, job: ProcessingJob, layer: str, assets: dict[str, RasterAsset]) -> bool:
        if layer == "difference":
            return "DIFFERENCE" in assets
        if layer == "mask":
            return "MASK" in assets
        observation_id = job.before_observation_id if layer == "before" else job.after_observation_id
        return self.rasters.source_for_observation(db, observation_id) is not None
