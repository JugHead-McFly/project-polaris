"""Store telescope and normal tracking preferences with each observatory.

Revision ID: 20260801_0005
Revises: 20260725_0004
Create Date: 2026-08-01
"""

from typing import Optional
from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_0005"
down_revision: Union[str, Sequence[str], None] = "20260725_0004"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column(
        "observatories",
        sa.Column("telescope_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "observatories",
        sa.Column(
            "tracking_preference",
            sa.String(length=20),
            nullable=False,
            server_default="not_sure",
        ),
    )
    if op.get_context().dialect.name == "postgresql":
        op.create_check_constraint(
            "ck_observatories_tracking_preference",
            "observatories",
            "tracking_preference IN "
            "('not_sure', 'alt_az', 'equatorial', 'both')",
        )
        op.alter_column(
            "observatories",
            "tracking_preference",
            server_default=None,
        )


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.drop_constraint(
            "ck_observatories_tracking_preference",
            "observatories",
            type_="check",
        )
    op.drop_column("observatories", "tracking_preference")
    op.drop_column("observatories", "telescope_model")
