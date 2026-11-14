import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NisarScene(Base):
    """Product found in the ASF DAAC catalogue."""

    __tablename__ = "nisar_scenes"
    __table_args__ = (
        Index("ix_nisar_scenes_footprint", "footprint", postgresql_using="gist"),
        Index("ix_nisar_scenes_acquisition_start", "acquisition_start"),
        Index(
            "ix_nisar_scenes_product_maturity_start",
            "product_type",
            "maturity",
            "acquisition_start",
        ),
        {"schema": "catalog"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)
    maturity: Mapped[str | None] = mapped_column(String(30))
    acquisition_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acquisition_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    orbit_direction: Mapped[str | None] = mapped_column(String(20))
    polarization: Mapped[list[str] | None] = mapped_column(JSONB)
    footprint: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    # `metadata` is reserved on the declarative base, so the attribute is renamed.
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    source_url: Mapped[str | None] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
