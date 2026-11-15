"""change_events: direction and mean change, so the map can colour without extra requests

Revision ID: a3d9e5b17c42
Revises: 8c1f2a7d4e90
Create Date: 2026-11-14 21:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3d9e5b17c42"
down_revision: str | None = "8c1f2a7d4e90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "change_events", sa.Column("direction", sa.String(length=10), nullable=True), schema="analysis"
    )
    op.add_column(
        "change_events", sa.Column("mean_change_db", sa.Float(), nullable=True), schema="analysis"
    )
    op.create_index(
        "ix_change_events_job_type", "change_events", ["job_id", "change_type"], schema="analysis"
    )
    # Existing rows: the value already lives in the per-polygon metric.
    op.execute(
        """
        UPDATE analysis.change_events AS c
        SET mean_change_db = m.value,
            direction = CASE WHEN m.value < 0 THEN 'DECREASE' ELSE 'INCREASE' END
        FROM analysis.change_metrics AS m
        WHERE m.change_event_id = c.id AND m.metric_name = 'mean_change_db' AND m.value IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_change_events_job_type", table_name="change_events", schema="analysis")
    op.drop_column("change_events", "mean_change_db", schema="analysis")
    op.drop_column("change_events", "direction", schema="analysis")
