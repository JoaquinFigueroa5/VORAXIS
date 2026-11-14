import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ASSET_TYPES = ("SOURCE", "BEFORE", "AFTER", "DIFFERENCE", "MASK", "CHANGE_VECTOR")


class RasterAsset(Base):
    """Reference to a raster object in MinIO. Raster bytes never live in Postgres."""

    __tablename__ = "raster_assets"
    __table_args__ = (
        Index("ix_raster_assets_job_id", "job_id"),
        Index("ix_raster_assets_observation_id", "observation_id"),
        {"schema": "processing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog.observations.id", ondelete="SET NULL")
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processing.processing_jobs.id", ondelete="SET NULL")
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str | None] = mapped_column(String(20))
    crs: Mapped[str | None] = mapped_column(String(50))
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
