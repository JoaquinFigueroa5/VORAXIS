import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

JOB_STATUSES = ("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED")

JOB_STEPS = (
    "DOWNLOADING",
    "PREPROCESSING",
    "ALIGNMENT",
    "CHANGE_DETECTION",
    "EVIDENCE_ANALYSIS",
    "EXPORTING",
)


class ProcessingJob(Base):
    """Asynchronous analysis tracked in Redis/RQ and in the database."""

    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="status_valid",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="progress_range"),
        Index("ix_processing_jobs_status", "status"),
        Index("ix_processing_jobs_created_at", "created_at"),
        {"schema": "processing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("geography.locations.id", ondelete="CASCADE"), nullable=False
    )
    before_observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog.observations.id"), nullable=False
    )
    after_observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog.observations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", server_default="PENDING"
    )
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    current_step: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    # What was asked for, and a summary of what the run produced.
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
