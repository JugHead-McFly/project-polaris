"""Immutable forecast windows and nightly satellite comparison evidence."""
from alembic import op
import sqlalchemy as sa

revision = "20261006_0011"
down_revision = "20261006_0010"
branch_labels = depends_on = None


def upgrade():
    op.create_table("nightly_forecasts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("observatory_id", sa.Uuid(), nullable=False),
        sa.Column("night_date", sa.Date(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("timezone_name", sa.String(64), nullable=False),
        sa.Column("forecasts", sa.JSON(), nullable=False),
        sa.Column("observation", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["observatory_id", "user_id"], ["observatories.id", "observatories.user_id"], ondelete="CASCADE", name="fk_nightly_forecast_owner"),
        sa.UniqueConstraint("observatory_id", "user_id", "night_date", name="uq_nightly_forecast_home_date"))
    op.create_index("ix_nightly_forecasts_user_id", "nightly_forecasts", ["user_id"])
    if op.get_context().dialect.name == "postgresql":
        owner = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"
        op.execute("ALTER TABLE nightly_forecasts ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE nightly_forecasts FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY nightly_forecasts_owner_isolation ON nightly_forecasts USING ({owner}) WITH CHECK ({owner})")
        op.execute("REVOKE ALL ON nightly_forecasts FROM PUBLIC, anon, authenticated")
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON nightly_forecasts TO polaris_app")


def downgrade():
    op.drop_table("nightly_forecasts")
