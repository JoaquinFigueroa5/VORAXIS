"""Export job rasters to object storage as Cloud Optimized GeoTIFFs and register them."""

from pathlib import Path

import numpy as np
import rasterio
import rasterio.shutil

from app.core.config import settings
from app.core.logging import get_logger
from app.core.storage import upload_file
from app.processing.quality_control import require_pair_loaded
from app.repositories.raster_repository import RasterRepository

logger = get_logger(__name__)


def write_cog(path: Path, array: np.ndarray, crs, transform, *, nodata, tags=None) -> Path:
    """Single-band COG with overviews. `nearest` overviews for integer masks."""
    path = Path(path)
    scratch = path.with_name(path.stem + ".scratch.tif")
    is_float = np.issubdtype(array.dtype, np.floating)
    profile = {
        "driver": "GTiff",
        "height": array.shape[0],
        "width": array.shape[1],
        "count": 1,
        "dtype": str(array.dtype),
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
    }
    try:
        with rasterio.open(scratch, "w", **profile) as sink:
            sink.write(array, 1)
            if tags:
                sink.update_tags(**tags)
        rasterio.shutil.copy(
            scratch,
            path,
            driver="COG",
            compress="DEFLATE",
            predictor="YES",
            blocksize=512,
            overview_resampling="average" if is_float else "nearest",
            bigtiff="IF_SAFER",
        )
    finally:
        scratch.unlink(missing_ok=True)
    return path


def run(db, context) -> None:
    before, _ = require_pair_loaded(context)
    if context.difference is None or context.change_mask is None:
        return

    rasters = RasterRepository()
    for asset in rasters.list_for_job(db, context.job_id):  # re-runs replace, never pile up
        rasters.delete(db, asset)

    shared = {
        "bucket": settings.minio_bucket,
        "shape": list(context.difference.shape),
        "polarization": context.polarization,
        "threshold_db": context.threshold_db,
        "baseline_db": context.baseline_db,
    }
    exports = (
        (
            "DIFFERENCE",
            "difference.tif",
            context.difference.astype("float32"),
            float("nan"),
            {"units": "dB", "quantity": "log-ratio after/before"},
        ),
        (
            "MASK",
            "change_mask.tif",
            context.change_mask.astype("uint8"),
            0,
            {"units": "boolean", "quantity": "changed"},
        ),
    )
    for asset_type, filename, array, nodata, tags in exports:
        local_path = write_cog(
            context.workdir / filename, array, before.crs, before.transform, nodata=nodata, tags=tags
        )
        key = f"jobs/{context.job_id}/{filename}"
        upload_file(local_path, key, content_type="image/tiff")
        rasters.create(
            db,
            asset_type=asset_type,
            storage_path=key,
            job_id=context.job_id,
            format="COG",
            crs=str(before.crs),
            metadata={**shared, **tags},
        )
    db.commit()
    logger.info("job %s exported %s raster assets", context.job_id, len(exports))
