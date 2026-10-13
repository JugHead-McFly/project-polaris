"""Account-owned historical stacks, kept outside verified raw exposure totals."""
from uuid import uuid4
from sqlalchemy import Column, ForeignKey, String, Float, JSON, UniqueConstraint, Uuid
from app.database.database import Base


class LegacyCapture(Base):
    __tablename__ = "legacy_capture_history"
    __table_args__ = (UniqueConstraint("user_id", "source_key", name="uq_legacy_history_owner_source"),)
    id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(Uuid, ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True)
    source_key = Column(String(64), nullable=False)
    target = Column(String(100), nullable=False)
    original_observation_time = Column(String(80), nullable=True)
    reported_integration_seconds = Column(Float, nullable=True)
    evidence_hash = Column(String(64), nullable=False)
    review_flags = Column(JSON, nullable=False)
