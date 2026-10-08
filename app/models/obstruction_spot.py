from uuid import uuid4

from sqlalchemy import Column, Uuid, String, Integer, JSON, DateTime, ForeignKeyConstraint, CheckConstraint
from app.database.database import Base
from app.models.hosted import utc_now


class ObstructionSpot(Base):
    __tablename__ = "obstruction_spots"
    __table_args__ = (
        ForeignKeyConstraint(["observatory_id", "user_id"], ["observatories.id", "observatories.user_id"], ondelete="CASCADE", name="fk_obstruction_spots_owner"),
        CheckConstraint("revision >= 1", name="ck_obstruction_spots_revision"),
        CheckConstraint("schema_version = 1", name="ck_obstruction_spots_schema"),
        CheckConstraint("source_quality IN ('manual_measured', 'synthetic', 'photo_estimate')", name="ck_obstruction_spots_source"),
    )
    id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(Uuid, nullable=False, index=True)
    observatory_id = Column(Uuid, nullable=False, index=True)
    name = Column(String(80), nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    schema_version = Column(Integer, nullable=False, default=1)
    source_quality = Column(String(30), nullable=False)
    profile = Column(JSON, nullable=False)
    home_binding = Column(JSON, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
