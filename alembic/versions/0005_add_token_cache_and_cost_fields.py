"""add cache token and cost fields to decision_log (T2.3 token logging)

Revision ID: 0005_add_token_cache_and_cost_fields
Revises: 74b26b81cb14
Create Date: 2026-04-19

Adds 3 nullable columns to decision_log:
  total_tokens_cache_read     — INTEGER: prompt-cache read tokens
  total_tokens_cache_creation — INTEGER: prompt-cache creation tokens
  cost_estimated_usd          — FLOAT: blended cost estimate

Uses batch_alter_table for SQLite + PostgreSQL compatibility.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0005_add_token_cache_and_cost_fields"
down_revision: str | None = "74b26b81cb14"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("decision_log") as batch_op:
        batch_op.add_column(sa.Column("total_tokens_cache_read", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("total_tokens_cache_creation", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cost_estimated_usd", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("decision_log") as batch_op:
        batch_op.drop_column("cost_estimated_usd")
        batch_op.drop_column("total_tokens_cache_creation")
        batch_op.drop_column("total_tokens_cache_read")
