"""Preserve historical stack metadata separately from verified raw exposures."""
from alembic import op
import sqlalchemy as sa

revision = "20261013_0012"
down_revision = "20261006_0011"
branch_labels = depends_on = None


def upgrade():
    op.create_table("legacy_capture_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("target", sa.String(100), nullable=False),
        sa.Column("original_observation_time", sa.String(80)),
        sa.Column("reported_integration_seconds", sa.Float()),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("review_flags", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "source_key", name="uq_legacy_history_owner_source"))
    op.create_index("ix_legacy_capture_history_user_id", "legacy_capture_history", ["user_id"])
    if op.get_context().dialect.name == "postgresql":
        owner = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"
        op.execute("ALTER TABLE legacy_capture_history ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE legacy_capture_history FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY legacy_capture_history_owner_isolation ON legacy_capture_history USING ({owner}) WITH CHECK ({owner})")
        op.execute("REVOKE ALL ON legacy_capture_history FROM PUBLIC, anon, authenticated")
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON legacy_capture_history TO polaris_app")


def downgrade():
    op.drop_table("legacy_capture_history")
