"""Allow the migration owner to rehearse the restricted runtime role.

Revision ID: 20260725_0004
Revises: 20260725_0003
Create Date: 2026-07-25
"""

from typing import Optional
from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_0004"
down_revision: Union[str, Sequence[str], None] = "20260725_0003"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                EXECUTE format(
                    'GRANT polaris_app TO %I',
                    current_user
                );
            END
            $$;
            """
        )
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                EXECUTE format(
                    'REVOKE polaris_app FROM %I',
                    current_user
                );
            END
            $$;
            """
        )
    )
