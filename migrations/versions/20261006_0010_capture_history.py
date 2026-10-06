"""Account-owned NAS capture summaries and scoped desktop sync credentials."""
from alembic import op
import sqlalchemy as sa

revision = "20261006_0010"
down_revision = "20260912_0009"
branch_labels = depends_on = None


def upgrade():
    op.create_table("capture_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("target", sa.String(100), nullable=False),
        sa.Column("session_name", sa.String(240), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filter_name", sa.String(60), nullable=False),
        sa.Column("frame_count", sa.Integer(), nullable=False),
        sa.Column("integration_seconds", sa.Float(), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "source_key", name="uq_capture_history_owner_source"))
    op.create_index("ix_capture_history_user_id", "capture_history", ["user_id"])
    op.create_table("library_sync_credentials",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("profiles.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)))
    if op.get_context().dialect.name == "postgresql":
        owner = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"
        for name in ("capture_history", "library_sync_credentials"):
            op.execute(sa.text(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY"))
            op.execute(sa.text(f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY"))
            op.execute(sa.text(f"CREATE POLICY {name}_owner_isolation ON {name} USING ({owner}) WITH CHECK ({owner})"))
            op.execute(sa.text(f"REVOKE ALL ON {name} FROM PUBLIC, anon, authenticated"))
            op.execute(sa.text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {name} TO polaris_app"))


def downgrade():
    op.drop_table("library_sync_credentials")
    op.drop_table("capture_history")
