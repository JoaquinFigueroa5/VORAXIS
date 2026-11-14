"""Export job rasters to MinIO as tiled GeoTIFFs and register them."""

import rasterio

from app.core.config import settings
from app.core.logging import get_logger
from app.core.storage import upload_file
from app.processing.quality_control import require_pair_loaded
from app.repositories.raster_repository import RasterRepository

logger = get_logger(__name__)


def _write_cog(path, array, template, dtype: str) -> None:
    profile = {
        "driver": "GTiff",
        "height": array.shape[0],
        "width": array.shape[1],
        "count": 1,
        "dtype": dtype,
        "crs": template.crs,
        "transform": template.transform,
        "nodata": 0 if dtype == "uint8" else None,
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as sink:
        sink.write(array.astype(dtype), 1)


def run(db, context) -> None:
    before, _ = require_pair_loaded(context)
    if context.difference is None or context.change_mask is None:
        return

    rasters = RasterRepository()
    exports = (
        ("DIFFERENCE", "difference.tif", context.difference, "float32"),
        ("MASK", "change_mask.tif", context.change_mask.astype("uint8"), "uint8"),
    )
    for asset_type, filename, array, dtype in exports:
        local_path = context.workdir / filename
        _write_cog(local_path, array, before, dtype)
        key = f"jobs/{context.job_id}/{filename}"
        upload_file(local_path, key, content_type="image/tiff")
        rasters.create(
            db,
            asset_type=asset_type,
            storage_path=key,
            job_id=context.job_id,
            format="COG",
            crs=str(before.crs),
            metadata={"bucket": settings.minio_bucket, "shape": list(array.shape)},
        )
    db.commit()
    logger.info("job %s exported %s raster assets to MinIO", context.job_id, len(exports))
