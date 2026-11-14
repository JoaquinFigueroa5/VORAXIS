import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChangeEvent(Base):
    """Geographic change detected by an analysis job.

    ``change_type`` is 'UNCLASSIFIED' unless a validated interpretation exists:
    a difference is not automatically a flood, a fire or an earthquake.
    """

    __tablename__ = "change_events"
    __table_args__ = (
        CheckConstraint(
            "valid_pixel_percentage IS NULL OR (valid_pixel_percentage >= 0 AND valid_pixel_percentage <= 100)",
            name="valid_pixel_percentage_range",
        ),
        Index("ix_change_events_geometry", "geometry", postgresql_using="gist"),
        Index("ix_change_events_job_id", "job_id"),
        {"schema": "analysis"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processing.processing_jobs.id", ondelete="CASCADE"), nullable=False
    )
    change_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="UNCLASSIFIED", server_default="UNCLASSIFIED"
    )
    geometry: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    area_km2: Mapped[float | None] = mapped_column(Float)
    change_score: Mapped[float | None] = mapped_column(Float)
    valid_pixel_percentage: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
