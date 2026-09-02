"""Preserve hourly forecast horizons for accuracy history.

Revision ID: 20260901_0008
Revises: 20260830_0007
Create Date: 2026-09-01
"""

from typing import Optional
from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260901_0008"
down_revision: Union[str, Sequence[str], None] = "20260830_0007"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


TABLE_NAME = "forecast_accuracy_snapshots"
OLD_UNIQUE = "uq_forecast_accuracy_observatory_hour"
NEW_UNIQUE = "uq_forecast_accuracy_observatory_hour_lead"
LEAD_CHECK = "ck_forecast_accuracy_lead_hour"


def upgrade() -> None:
    op.add_column(
        TABLE_NAME,
        sa.Column(
            "forecast_lead_hour",
            sa.Integer(),
            nullable=True,
            server_default="0",
        ),
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE_NAME} NO FORCE ROW LEVEL SECURITY"
            )
        )
        op.execute(
            sa.text(
                f"UPDATE {TABLE_NAME} SET forecast_lead_hour = "
                "GREATEST(0, CEIL(EXTRACT(EPOCH FROM "
                "(forecast_for - forecast_created_at)) / 3600.0)::integer)"
            )
        )
    else:
        op.execute(
            sa.text(
                f"UPDATE {TABLE_NAME} SET forecast_lead_hour = "
                "MAX(0, CAST(((julianday(forecast_for) - "
                "julianday(forecast_created_at)) * 24.0) + "
                "0.999999 AS INTEGER))"
            )
        )

    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.alter_column(
            "forecast_lead_hour",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_constraint(OLD_UNIQUE, type_="unique")
        batch_op.create_unique_constraint(
            NEW_UNIQUE,
            [
                "observatory_id",
                "user_id",
                "forecast_for",
                "forecast_lead_hour",
            ],
        )
        batch_op.create_check_constraint(
            LEAD_CHECK,
            "forecast_lead_hour >= 0",
        )
    if op.get_context().dialect.name == "postgresql":
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY"
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"DELETE FROM {TABLE_NAME} WHERE id IN ("
            "SELECT id FROM ("
            "SELECT id, ROW_NUMBER() OVER ("
            "PARTITION BY observatory_id, user_id, forecast_for "
            "ORDER BY forecast_lead_hour ASC, forecast_created_at DESC"
            ") AS duplicate_rank "
            f"FROM {TABLE_NAME}"
            ") ranked WHERE duplicate_rank > 1)"
        )
    )
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.drop_constraint(LEAD_CHECK, type_="check")
        batch_op.drop_constraint(NEW_UNIQUE, type_="unique")
        batch_op.create_unique_constraint(
            OLD_UNIQUE,
            ["observatory_id", "user_id", "forecast_for"],
        )
        batch_op.drop_column("forecast_lead_hour")
