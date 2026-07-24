"""Baseline the existing Polaris v1.6 schema.

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from typing import Optional
from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("date", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("observatory", sa.String(), nullable=True),
        sa.Column("bortle_class", sa.Integer(), nullable=True),
        sa.Column("moon_phase", sa.String(), nullable=True),
        sa.Column("weather_summary", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sessions_session_id",
        "sessions",
        ["session_id"],
        unique=True,
    )

    op.create_table(
        "candidate_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("bortle_class", sa.Integer(), nullable=True),
        sa.Column("access_hours", sa.String(), nullable=True),
        sa.Column("vehicle_requirement", sa.String(), nullable=True),
        sa.Column("property_access", sa.String(), nullable=True),
        sa.Column(
            "parking_setup_confirmed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column("horizon_confirmed", sa.Boolean(), nullable=False),
        sa.Column("access_confirmed", sa.Boolean(), nullable=False),
        sa.Column("amenities_confirmed", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("visited_at", sa.DateTime(), nullable=True),
        sa.Column("star_rating", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "captures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polaris_id", sa.String(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("object_name", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("asset_path", sa.String(), nullable=True),
        sa.Column("observation_utc", sa.String(), nullable=True),
        sa.Column("gain", sa.Float(), nullable=True),
        sa.Column("ra", sa.Float(), nullable=True),
        sa.Column("dec", sa.Float(), nullable=True),
        sa.Column("telescope", sa.String(), nullable=True),
        sa.Column("firmware", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("exposure_seconds", sa.Integer(), nullable=True),
        sa.Column("sub_exposure_seconds", sa.Integer(), nullable=True),
        sa.Column("subframe_count", sa.Integer(), nullable=True),
        sa.Column(
            "total_integration_seconds",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("filter_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_captures_polaris_id",
        "captures",
        ["polaris_id"],
        unique=True,
    )

    op.create_table(
        "capture_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("capture_id", sa.Integer(), nullable=False),
        sa.Column("stars_detected", sa.Integer(), nullable=True),
        sa.Column("median_fwhm", sa.Float(), nullable=True),
        sa.Column("eccentricity", sa.Float(), nullable=True),
        sa.Column("median_roundness", sa.Float(), nullable=True),
        sa.Column("median_sharpness", sa.Float(), nullable=True),
        sa.Column("background_level", sa.Float(), nullable=True),
        sa.Column("background_noise", sa.Float(), nullable=True),
        sa.Column(
            "relative_background_noise",
            sa.Float(),
            nullable=True,
        ),
        sa.Column("background_gradient", sa.Float(), nullable=True),
        sa.Column("clipped_pixel_fraction", sa.Float(), nullable=True),
        sa.Column("snr", sa.Float(), nullable=True),
        sa.Column("star_sample_count", sa.Integer(), nullable=True),
        sa.Column("trailing_detected", sa.Boolean(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("legacy_quality_score", sa.Integer(), nullable=True),
        sa.Column("scoring_version", sa.String(), nullable=True),
        sa.Column("analysis_confidence", sa.String(), nullable=True),
        sa.Column("recommendation", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["capture_id"], ["captures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_capture_analyses_capture_id",
        "capture_analyses",
        ["capture_id"],
        unique=False,
    )
    op.create_index(
        "ix_capture_analyses_id",
        "capture_analyses",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_capture_analyses_id",
        table_name="capture_analyses",
    )
    op.drop_index(
        "ix_capture_analyses_capture_id",
        table_name="capture_analyses",
    )
    op.drop_table("capture_analyses")
    op.drop_index("ix_captures_polaris_id", table_name="captures")
    op.drop_table("captures")
    op.drop_table("candidate_sites")
    op.drop_index("ix_sessions_session_id", table_name="sessions")
    op.drop_table("sessions")
