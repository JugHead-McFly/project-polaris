"""Owner-isolated reviewed obstruction surveys per observing-home setup spot."""
from alembic import op
import sqlalchemy as sa

revision = "20261008_0012"
down_revision = "20261006_0011"
branch_labels = depends_on = None


def upgrade():
    op.create_table("obstruction_spots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("observatory_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("source_quality", sa.String(30), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("home_binding", sa.JSON(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["observatory_id", "user_id"], ["observatories.id", "observatories.user_id"], ondelete="CASCADE", name="fk_obstruction_spots_owner"),
        sa.CheckConstraint("revision >= 1", name="ck_obstruction_spots_revision"),
        sa.CheckConstraint("schema_version = 1", name="ck_obstruction_spots_schema"),
        sa.CheckConstraint("source_quality IN ('manual_measured', 'synthetic', 'photo_estimate')", name="ck_obstruction_spots_source"))
    op.create_index("ix_obstruction_spots_user_id", "obstruction_spots", ["user_id"])
    op.create_index("ix_obstruction_spots_observatory_id", "obstruction_spots", ["observatory_id"])
    if op.get_context().dialect.name == "postgresql":
        owner = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"
        op.execute("ALTER TABLE obstruction_spots ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE obstruction_spots FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY obstruction_spots_owner_isolation ON obstruction_spots USING ({owner}) WITH CHECK ({owner})")
        op.execute("REVOKE ALL ON obstruction_spots FROM PUBLIC, anon, authenticated")
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON obstruction_spots TO polaris_app")


def downgrade():
    op.drop_table("obstruction_spots")
