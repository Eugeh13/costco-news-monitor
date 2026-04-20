"""add 8 missing fields to decision_log (Op C hotfix)

Revision ID: 0003_add_missing_decision_log_fields
Revises: 0002_add_decision_log_and_feedback
Create Date: 2026-04-19

Fields added:
  article_content_snippet — TEXT nullable
  within_radius           — BOOLEAN nullable
  is_duplicate            — BOOLEAN nullable
  total_tokens_input      — INTEGER nullable
  total_tokens_output     — INTEGER nullable
  total_latency_ms        — INTEGER nullable
  telegram_sent           — BOOLEAN NOT NULL default False
  error_stage             — VARCHAR(100) nullable

SQLite note: ALTER TABLE ADD COLUMN works fine for nullable columns and columns
with a constant default (SQLite 3.37+). No batch_alter_table needed.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_missing_decision_log_fields"
down_revision: str | None = "0002_add_decision_log_and_feedback"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("decision_log") as batch_op:
        batch_op.add_column(sa.Column("article_content_snippet", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("within_radius", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("is_duplicate", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("total_tokens_input", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("total_tokens_output", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("total_latency_ms", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "telegram_sent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("error_stage", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("decision_log") as batch_op:
        batch_op.drop_column("error_stage")
        batch_op.drop_column("telegram_sent")
        batch_op.drop_column("total_latency_ms")
        batch_op.drop_column("total_tokens_output")
        batch_op.drop_column("total_tokens_input")
        batch_op.drop_column("is_duplicate")
        batch_op.drop_column("within_radius")
        batch_op.drop_column("article_content_snippet")
