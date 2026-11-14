import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuxiliaryEvent(Base):
    """External event (fire, precipitation, earthquake) used as context only."""

    __tablename__ = "auxiliary_events"
    __table_args__ = (
        Index("ix_auxiliary_events_geometry", "geometry", postgresql_using="gist"),
        Index("ix_auxiliary_events_event_date", "event_date"),
        Index("ix_auxiliary_events_source_external", "source", "external_id"),
        {"schema": "evidence"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Generic geometry: points for FIRMS/USGS, areas for aggregated precipitation.
    geometry: Mapped[Any] = mapped_column(Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=False)
    magnitude: Mapped[float | None] = mapped_column(Float)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
