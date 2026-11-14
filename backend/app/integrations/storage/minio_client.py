from app.core.storage import (
    download_object,
    ensure_bucket,
    get_minio,
    object_url,
    upload_file,
)


class MinioStorage:
    """Small facade so workers depend on one name, not on minio internals."""

    def ensure_bucket(self) -> None:
        ensure_bucket()

    def upload_file(self, local_path, key: str, content_type: str = "application/octet-stream") -> str:
        return upload_file(local_path, key, content_type)

    def download_object(self, key: str, destination):
        return download_object(key, destination)

    def url(self, key: str) -> str:
        return object_url(key)

    def client(self):
        return get_minio()
