"""Preserve satellite cloud references alongside original model comparisons.

Revision ID: 20260912_0009
Revises: 20260901_0008
"""

from alembic import op
import sqlalchemy as sa

revision = "20260912_0009"
down_revision = "20260901_0008"
branch_labels = None
depends_on = None


def upgrade():
    # Existing forced tenant RLS and table grants apply to this column too.
    op.add_column(
        "forecast_accuracy_snapshots",
        sa.Column("satellite_cloud_observation", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("forecast_accuracy_snapshots", "satellite_cloud_observation")
