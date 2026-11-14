from app.core.exceptions import ProcessingError
from app.core.logging import get_logger
from app.core.storage import download_object
from app.repositories.raster_repository import RasterRepository

logger = get_logger(__name__)

SUPPORTED_FORMATS = ("TIFF", "COG")


def run(db, context) -> None:
    """Copy both observations' SOURCE rasters from MinIO into the job workdir."""
    rasters = RasterRepository()
    for observation_id, name in (
        (context.before_observation_id, "before"),
        (context.after_observation_id, "after"),
    ):
        asset = rasters.source_for_observation(db, observation_id)
        if asset is None:
            raise ProcessingError(
                f"observation {observation_id} has no SOURCE raster asset; "
                "register the file in processing.raster_assets first"
            )
        if (asset.format or "").upper() not in SUPPORTED_FORMATS:
            raise ProcessingError(
                f"observation {observation_id} source is {asset.format}; "
                "only GeoTIFF/COG sources are supported so far"
            )
        download_object(asset.storage_path, context.workdir / f"{name}.tif")
        logger.info("downloaded %s raster for observation %s", name, observation_id)
