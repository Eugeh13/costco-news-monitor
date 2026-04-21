"""add geolocation fields to decision_log

Revision ID: 74b26b81cb14
Revises: 0004_add_geolocation_fields
Create Date: 2026-04-20 18:23:39.429268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74b26b81cb14'
down_revision: Union[str, Sequence[str], None] = '0004_add_geolocation_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('decision_log', sa.Column('approximate_location', sa.String(length=200), nullable=True))
    op.add_column('decision_log', sa.Column('exact_location_lat', sa.Float(), nullable=True))
    op.add_column('decision_log', sa.Column('exact_location_lng', sa.Float(), nullable=True))
    op.add_column('decision_log', sa.Column('geolocation_confidence', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('decision_log') as batch_op:
        batch_op.drop_column('geolocation_confidence')
        batch_op.drop_column('exact_location_lng')
        batch_op.drop_column('exact_location_lat')
        batch_op.drop_column('approximate_location')
