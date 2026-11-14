"""MinIO helpers. Object keys are stored in raster_assets.storage_path."""

from functools import lru_cache
from pathlib import Path

from minio import Minio

from app.core.config import settings


@lru_cache
def get_minio() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_user,
        secret_key=settings.minio_password,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    client = get_minio()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def upload_file(local_path: Path, key: str, content_type: str = "application/octet-stream") -> str:
    get_minio().fput_object(
        settings.minio_bucket,
        key,
        str(local_path),
        content_type=content_type,
    )
    return key


def download_object(key: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    get_minio().fget_object(settings.minio_bucket, key, str(destination))
    return destination


def object_url(key: str) -> str:
    scheme = "https" if settings.minio_secure else "http"
    return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{key}"
