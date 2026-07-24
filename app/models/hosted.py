from datetime import datetime
from datetime import timezone
from uuid import uuid4

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import Uuid

from app.database.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(Uuid, primary_key=True)
    display_name = Column(String(100), nullable=True)
    onboarding_state = Column(
        String(30),
        nullable=False,
        default="not_started",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class HostedObservatory(Base):
    __tablename__ = "observatories"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "user_id",
            name="uq_observatories_id_user_id",
        ),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="ck_observatories_latitude",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_observatories_longitude",
        ),
        CheckConstraint(
            "bortle_class IS NULL OR "
            "(bortle_class >= 1 AND bortle_class <= 9)",
            name="ck_observatories_bortle_class",
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    coordinates_are_approximate = Column(
        Boolean,
        nullable=False,
        default=False,
    )
    elevation_m = Column(Float, nullable=True)
    timezone_name = Column(String(64), nullable=False)
    bortle_class = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["observatory_id", "user_id"],
            ["observatories.id", "observatories.user_id"],
            name="fk_recommendation_runs_observatory_owner",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "id",
            "user_id",
            name="uq_recommendation_runs_id_user_id",
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observatory_id = Column(Uuid, nullable=False, index=True)
    planned_for = Column(DateTime(timezone=True), nullable=False)
    forecast_observed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    outcome = Column(String(30), nullable=False)
    primary_target = Column(String(100), nullable=True)
    explanation = Column(JSON, nullable=False, default=dict)
    input_provenance = Column(JSON, nullable=False, default=dict)
    planner_version = Column(String(30), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"
    __table_args__ = (
        ForeignKeyConstraint(
            ["observatory_id", "user_id"],
            ["observatories.id", "observatories.user_id"],
            name="fk_recommendation_feedback_observatory_owner",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["recommendation_run_id", "user_id"],
            ["recommendation_runs.id", "recommendation_runs.user_id"],
            name="fk_recommendation_feedback_run_owner",
            ondelete="CASCADE",
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observatory_id = Column(Uuid, nullable=False, index=True)
    recommendation_run_id = Column(Uuid, nullable=False, index=True)
    useful = Column(Boolean, nullable=False)
    reason = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
