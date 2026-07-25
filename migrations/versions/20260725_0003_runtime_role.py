"""Add the restricted hosted application database role.

Revision ID: 20260725_0003
Revises: 20260724_0002
Create Date: 2026-07-25
"""

from typing import Optional
from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_0003"
down_revision: Union[str, Sequence[str], None] = "20260724_0002"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


HOSTED_TABLES = (
    "profiles",
    "observatories",
    "recommendation_runs",
    "recommendation_feedback",
)


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname = 'polaris_app'
                ) THEN
                    CREATE ROLE polaris_app
                        NOLOGIN
                        NOSUPERUSER
                        NOCREATEDB
                        NOCREATEROLE
                        NOINHERIT
                        NOBYPASSRLS;
                END IF;
            END
            $$;
            """
        )
    )
    op.execute(sa.text("GRANT USAGE ON SCHEMA public TO polaris_app"))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE "
            f"ON TABLE {', '.join(HOSTED_TABLES)} "
            "TO polaris_app"
        )
    )
    op.execute(
        sa.text(
            "REVOKE ALL ON TABLE "
            "sessions, candidate_sites, captures, capture_analyses "
            "FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            "REVOKE ALL ON TABLE "
            f"{', '.join(HOSTED_TABLES)} "
            "FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname = 'anon'
                ) THEN
                    REVOKE ALL ON TABLE
                        sessions,
                        candidate_sites,
                        captures,
                        capture_analyses,
                        profiles,
                        observatories,
                        recommendation_runs,
                        recommendation_feedback
                    FROM anon;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_roles
                    WHERE rolname = 'authenticated'
                ) THEN
                    REVOKE ALL ON TABLE
                        sessions,
                        candidate_sites,
                        captures,
                        capture_analyses,
                        profiles,
                        observatories,
                        recommendation_runs,
                        recommendation_feedback
                    FROM authenticated;
                END IF;
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
            "REVOKE SELECT, INSERT, UPDATE, DELETE "
            f"ON TABLE {', '.join(HOSTED_TABLES)} "
            "FROM polaris_app"
        )
    )
    op.execute(
        sa.text("REVOKE USAGE ON SCHEMA public FROM polaris_app")
    )
    op.execute(sa.text("DROP ROLE IF EXISTS polaris_app"))
