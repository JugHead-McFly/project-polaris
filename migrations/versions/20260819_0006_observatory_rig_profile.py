"""Store selected rig profile key with each observatory.

Revision ID: 20260819_0006
Revises: 20260801_0005
Create Date: 2026-08-19
"""

from typing import Optional
from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260819_0006"
down_revision: Union[str, Sequence[str], None] = "20260801_0005"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column(
        "observatories",
        sa.Column("rig_profile_key", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("observatories", "rig_profile_key")
