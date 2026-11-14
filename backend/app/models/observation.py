import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

STORAGE_STATUSES = ("DISCOVERED", "READY", "FAILED")


class Observation(Base):
    """Acquisition prepared for analysis within an AOI."""

    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint(
            "storage_status IN ('DISCOVERED', 'READY', 'FAILED')",
            name="storage_status_valid",
        ),
        Index("ix_observations_acquisition_date", "acquisition_date"),
        Index("ix_observations_location_id", "location_id"),
        {"schema": "catalog"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog.nisar_scenes.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("geography.locations.id", ondelete="SET NULL")
    )
    acquisition_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processing_version: Mapped[str | None] = mapped_column(String(100))
    storage_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DISCOVERED", server_default="DISCOVERED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
