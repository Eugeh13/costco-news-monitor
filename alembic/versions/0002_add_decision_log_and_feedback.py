"""add decision_log and human_feedback tables

Revision ID: 0002_add_decision_log_and_feedback
Revises: 0001_initial_schema
Create Date: 2026-04-19

Notes:
  - Enums stored as VARCHAR (native_enum=False) for SQLite + PostgreSQL compat.
  - Unique constraint on (run_id, article_url) enables UPSERT-by-key pattern.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_decision_log_and_feedback"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | None = None
depends_on: str | None = None

# VARCHAR enums — no native PostgreSQL ENUM so SQLite works identically
_STAGE_VALUES = ("scraped", "triage", "deep_analysis", "geolocation", "dedup", "notification", "error")
_DECISION_VALUES = ("irrelevant", "duplicate", "out_of_radius", "no_geo", "alerted", "error", "pending")
_SHOULD_HAVE_VALUES = ("alerted", "dismissed", "escalated")


def upgrade() -> None:
    op.create_table(
        "decision_log",
        sa.Column("id", sa.Integer(), nullable=False),

        # Run identity
        sa.Column("run_id", sa.String(36), nullable=False),

        # Article metadata
        sa.Column("article_url", sa.Text(), nullable=False),
        sa.Column("article_title", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),

        # Pipeline tracking (VARCHAR for cross-DB compat)
        sa.Column("stage_reached", sa.String(30), nullable=False, server_default="scraped"),
        sa.Column("final_decision", sa.String(30), nullable=False, server_default="pending"),

        # Triage
        sa.Column("triage_passed", sa.Boolean(), nullable=True),
        sa.Column("triage_reason", sa.Text(), nullable=True),

        # Deep analysis
        sa.Column("incident_type", sa.String(50), nullable=True),
        sa.Column("severity_score", sa.Integer(), nullable=True),
        sa.Column("affects_operations", sa.Boolean(), nullable=True),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),

        # Geolocation
        sa.Column("geo_lat", sa.Float(), nullable=True),
        sa.Column("geo_lon", sa.Float(), nullable=True),
        sa.Column("geo_address", sa.Text(), nullable=True),
        sa.Column("nearest_costco", sa.String(100), nullable=True),
        sa.Column("nearest_costco_dist_m", sa.Float(), nullable=True),

        # Error
        sa.Column("error_message", sa.Text(), nullable=True),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),

        # Constraints
        sa.CheckConstraint(
            f"stage_reached IN {_STAGE_VALUES}",
            name="ck_decision_log_stage_reached",
        ),
        sa.CheckConstraint(
            f"final_decision IN {_DECISION_VALUES}",
            name="ck_decision_log_final_decision",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "article_url", name="uq_decision_log_run_url"),
    )
    op.create_index("ix_decision_log_run_id", "decision_log", ["run_id"])
    op.create_index("ix_decision_log_final_decision", "decision_log", ["final_decision"])
    op.create_index("ix_decision_log_stage_reached", "decision_log", ["stage_reached"])

    op.create_table(
        "human_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "decision_log_id",
            sa.Integer(),
            sa.ForeignKey("decision_log.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("should_have_been", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"should_have_been IS NULL OR should_have_been IN {_SHOULD_HAVE_VALUES}",
            name="ck_human_feedback_should_have_been",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_human_feedback_decision_log_id", "human_feedback", ["decision_log_id"])


def downgrade() -> None:
    op.drop_table("human_feedback")
    op.drop_index("ix_decision_log_stage_reached", table_name="decision_log")
    op.drop_index("ix_decision_log_final_decision", table_name="decision_log")
    op.drop_index("ix_decision_log_run_id", table_name="decision_log")
    op.drop_table("decision_log")
