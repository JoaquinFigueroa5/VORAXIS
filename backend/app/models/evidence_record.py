import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvidenceRecord(Base):
    """Link between a detected change and a contextual event.

    ``evidence_score`` is a heuristic, not a calibrated probability.
    """

    __tablename__ = "evidence_records"
    __table_args__ = (
        UniqueConstraint("change_event_id", "auxiliary_event_id", name="uq_evidence_pair"),
        {"schema": "evidence"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis.change_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    auxiliary_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.auxiliary_events.id", ondelete="CASCADE"), nullable=False
    )
    spatial_relation: Mapped[str] = mapped_column(String(50), nullable=False)
    distance_km: Mapped[float | None] = mapped_column(Float)
    time_difference_hours: Mapped[float | None] = mapped_column(Float)
    evidence_score: Mapped[float | None] = mapped_column(Float)
    explanation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
