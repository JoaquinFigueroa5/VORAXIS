"""processing_jobs: keep the request parameters and a result summary

Revision ID: 8c1f2a7d4e90
Revises: 0435d0c9fab4
Create Date: 2026-11-14 17:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8c1f2a7d4e90"
down_revision: str | None = "0435d0c9fab4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs",
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="processing",
    )
    op.add_column(
        "processing_jobs",
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="processing",
    )


def downgrade() -> None:
    op.drop_column("processing_jobs", "result", schema="processing")
    op.drop_column("processing_jobs", "parameters", schema="processing")
