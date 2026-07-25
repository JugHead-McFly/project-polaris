"""Add the isolated hosted-alpha tenant schema.

Revision ID: 20260724_0002
Revises: 20260724_0001
Create Date: 2026-07-24
"""

from typing import Optional
from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_0002"
down_revision: Union[str, Sequence[str], None] = "20260724_0001"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


TENANT_TABLES = (
    "profiles",
    "observatories",
    "recommendation_runs",
    "recommendation_feedback",
)
LOCAL_ONLY_TABLES = (
    "sessions",
    "candidate_sites",
    "captures",
    "capture_analyses",
)
OWNER_EXPRESSION = (
    "user_id = NULLIF("
    "current_setting('app.current_user_id', true), ''"
    ")::uuid"
)


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column(
            "onboarding_state",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "observatories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "coordinates_are_approximate",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column("elevation_m", sa.Float(), nullable=True),
        sa.Column(
            "timezone_name",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("bortle_class", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "bortle_class IS NULL OR "
            "(bortle_class >= 1 AND bortle_class <= 9)",
            name="ck_observatories_bortle_class",
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="ck_observatories_latitude",
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_observatories_longitude",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            name="uq_observatories_id_user_id",
        ),
    )
    op.create_index(
        "ix_observatories_user_id",
        "observatories",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "recommendation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("observatory_id", sa.Uuid(), nullable=False),
        sa.Column(
            "planned_for",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "forecast_observed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column(
            "primary_target",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("input_provenance", sa.JSON(), nullable=False),
        sa.Column(
            "planner_version",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["observatory_id", "user_id"],
            ["observatories.id", "observatories.user_id"],
            name="fk_recommendation_runs_observatory_owner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            name="uq_recommendation_runs_id_user_id",
        ),
    )
    op.create_index(
        "ix_recommendation_runs_observatory_id",
        "recommendation_runs",
        ["observatory_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_runs_user_id",
        "recommendation_runs",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("observatory_id", sa.Uuid(), nullable=False),
        sa.Column(
            "recommendation_run_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column("useful", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["observatory_id", "user_id"],
            ["observatories.id", "observatories.user_id"],
            name="fk_recommendation_feedback_observatory_owner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_run_id", "user_id"],
            ["recommendation_runs.id", "recommendation_runs.user_id"],
            name="fk_recommendation_feedback_run_owner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendation_feedback_observatory_id",
        "recommendation_feedback",
        ["observatory_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_feedback_recommendation_run_id",
        "recommendation_feedback",
        ["recommendation_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_feedback_user_id",
        "recommendation_feedback",
        ["user_id"],
        unique=False,
    )

    if op.get_context().dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TABLE alembic_version "
                "ENABLE ROW LEVEL SECURITY"
            )
        )
        for table_name in LOCAL_ONLY_TABLES:
            op.execute(
                sa.text(
                    f"ALTER TABLE {table_name} "
                    "ENABLE ROW LEVEL SECURITY"
                )
            )
            op.execute(
                sa.text(
                    f"ALTER TABLE {table_name} "
                    "FORCE ROW LEVEL SECURITY"
                )
            )
        for table_name in TENANT_TABLES:
            op.execute(
                sa.text(
                    f"ALTER TABLE {table_name} "
                    "ENABLE ROW LEVEL SECURITY"
                )
            )
            op.execute(
                sa.text(
                    f"ALTER TABLE {table_name} "
                    "FORCE ROW LEVEL SECURITY"
                )
            )
            op.execute(
                sa.text(
                    f"CREATE POLICY {table_name}_owner_isolation "
                    f"ON {table_name} "
                    f"USING ({OWNER_EXPRESSION}) "
                    f"WITH CHECK ({OWNER_EXPRESSION})"
                )
            )


def downgrade() -> None:
    op.drop_index(
        "ix_recommendation_feedback_user_id",
        table_name="recommendation_feedback",
    )
    op.drop_index(
        "ix_recommendation_feedback_recommendation_run_id",
        table_name="recommendation_feedback",
    )
    op.drop_index(
        "ix_recommendation_feedback_observatory_id",
        table_name="recommendation_feedback",
    )
    op.drop_table("recommendation_feedback")
    op.drop_index(
        "ix_recommendation_runs_user_id",
        table_name="recommendation_runs",
    )
    op.drop_index(
        "ix_recommendation_runs_observatory_id",
        table_name="recommendation_runs",
    )
    op.drop_table("recommendation_runs")
    op.drop_index(
        "ix_observatories_user_id",
        table_name="observatories",
    )
    op.drop_table("observatories")
    op.drop_table("profiles")
