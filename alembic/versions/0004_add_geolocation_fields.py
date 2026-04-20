"""add granular geolocation fields to analysis_results (T1.8)

Revision ID: 0004_add_geolocation_fields
Revises: 0003_add_missing_decision_log_fields
Create Date: 2026-04-20

Adds 4 nullable Float/String columns to analysis_results:
  approximate_location    — VARCHAR(200): colonia/zona text (e.g. "Valle Oriente, San Pedro")
  exact_location_lat      — FLOAT: latitude when LLM confidence is high
  exact_location_lng      — FLOAT: longitude when LLM confidence is high
  geolocation_confidence  — FLOAT: 0.0-1.0 confidence score from geolocate_incident()

Uses batch_alter_table for SQLite compatibility (Op C pattern).
All columns nullable=True — no existing rows are broken.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_geolocation_fields"
down_revision: str | None = "0003_add_missing_decision_log_fields"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_results") as batch_op:
        batch_op.add_column(sa.Column("approximate_location", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("exact_location_lat", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("exact_location_lng", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("geolocation_confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("analysis_results") as batch_op:
        batch_op.drop_column("geolocation_confidence")
        batch_op.drop_column("exact_location_lng")
        batch_op.drop_column("exact_location_lat")
        batch_op.drop_column("approximate_location")
