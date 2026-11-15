"""change_events: keep why the classifier said what it said

Revision ID: b7e2c4f19a03
Revises: a3d9e5b17c42
Create Date: 2026-11-15 18:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b7e2c4f19a03"
down_revision: str | None = "a3d9e5b17c42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "change_events", sa.Column("classification", JSONB(), nullable=True), schema="analysis"
    )
    # Existing rows: the type is known and needs no reason to be readable.
    op.execute(
        """
        UPDATE analysis.change_events
        SET classification = jsonb_build_object(
            'type', change_type,
            'confidence', 'NONE',
            'reasons', '[]'::jsonb
        )
        WHERE classification IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("change_events", "classification", schema="analysis")
