"""Add tenant-isolated forecast accuracy history.

Revision ID: 20260830_0007
Revises: 20260819_0006
Create Date: 2026-08-30
"""

from typing import Optional
from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260830_0007"
down_revision: Union[str, Sequence[str], None] = "20260819_0006"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


TABLE_NAME = "forecast_accuracy_snapshots"
OWNER_EXPRESSION = (
    "user_id = NULLIF("
    "current_setting('app.current_user_id', true), ''"
    ")::uuid"
)


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("observatory_id", sa.Uuid(), nullable=False),
        sa.Column("forecast_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "forecast_created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("forecast_provider", sa.String(length=40), nullable=True),
        sa.Column("forecast_temperature_f", sa.Float(), nullable=True),
        sa.Column(
            "forecast_cloud_cover_percent",
            sa.Float(),
            nullable=True,
        ),
        sa.Column("forecast_humidity_percent", sa.Float(), nullable=True),
        sa.Column("forecast_dew_point_f", sa.Float(), nullable=True),
        sa.Column("forecast_wind_speed_mph", sa.Float(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_provider", sa.String(length=40), nullable=True),
        sa.Column("observed_temperature_f", sa.Float(), nullable=True),
        sa.Column(
            "observed_cloud_cover_percent",
            sa.Float(),
            nullable=True,
        ),
        sa.Column("observed_humidity_percent", sa.Float(), nullable=True),
        sa.Column("observed_dew_point_f", sa.Float(), nullable=True),
        sa.Column("observed_wind_speed_mph", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'matched', 'expired')",
            name="ck_forecast_accuracy_status",
        ),
        sa.ForeignKeyConstraint(
            ["observatory_id", "user_id"],
            ["observatories.id", "observatories.user_id"],
            name="fk_forecast_accuracy_observatory_owner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "observatory_id",
            "user_id",
            "forecast_for",
            name="uq_forecast_accuracy_observatory_hour",
        ),
    )
    op.create_index(
        "ix_forecast_accuracy_snapshots_forecast_for",
        TABLE_NAME,
        ["forecast_for"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_accuracy_snapshots_observatory_id",
        TABLE_NAME,
        ["observatory_id"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_accuracy_snapshots_user_id",
        TABLE_NAME,
        ["user_id"],
        unique=False,
    )

    if op.get_context().dialect.name == "postgresql":
        op.execute(sa.text(f"ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY {TABLE_NAME}_owner_isolation "
                f"ON {TABLE_NAME} USING ({OWNER_EXPRESSION}) "
                f"WITH CHECK ({OWNER_EXPRESSION})"
            )
        )
        op.execute(
            sa.text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {TABLE_NAME} "
                "TO polaris_app"
            )
        )
        op.execute(sa.text(f"REVOKE ALL ON TABLE {TABLE_NAME} FROM PUBLIC"))
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') "
                f"THEN REVOKE ALL ON TABLE {TABLE_NAME} FROM anon; END IF; "
                "IF EXISTS (SELECT 1 FROM pg_roles "
                "WHERE rolname = 'authenticated') "
                f"THEN REVOKE ALL ON TABLE {TABLE_NAME} FROM authenticated; "
                "END IF; END $$;"
            )
        )


def downgrade() -> None:
    op.drop_index(
        "ix_forecast_accuracy_snapshots_user_id",
        table_name=TABLE_NAME,
    )
    op.drop_index(
        "ix_forecast_accuracy_snapshots_observatory_id",
        table_name=TABLE_NAME,
    )
    op.drop_index(
        "ix_forecast_accuracy_snapshots_forecast_for",
        table_name=TABLE_NAME,
    )
    op.drop_table(TABLE_NAME)
