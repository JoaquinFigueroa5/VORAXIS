"""Backend settings. All values come from environment variables (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "SpaceApps NISAR API"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg://spaceapps:spaceapps@localhost:5432/spaceapps"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue: str = "analysis"

    minio_endpoint: str = "localhost:9000"
    minio_user: str = "minioadmin"
    minio_password: str = "minioadmin"
    minio_bucket: str = "spaceapps-data"
    minio_secure: bool = False

    # Local cache for downloaded .h5 granules (relative to the backend workdir).
    nisar_data_dir: str = "data/nisar"
    # Keep downloaded .h5 granules after they are converted to a COG. They are
    # 2-7 GB each and only needed again to re-ingest with other options, so a
    # server with a small disk sets this to false.
    keep_downloaded_granules: bool = True

    # Local copies of COGs used to render map tiles; empty = system temp dir.
    tile_cache_dir: str = ""

    # Seconds a context lookup (ASF / USGS / POWER / FIRMS by point) is reused.
    context_cache_ttl: int = 600

    earthdata_username: str = ""
    earthdata_password: str = ""
    firms_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
