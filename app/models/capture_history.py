from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, Uuid
from app.database.database import Base
from app.models.hosted import utc_now


class HostedCaptureSession(Base):
    __tablename__ = "capture_history"
    __table_args__ = (UniqueConstraint("user_id", "source_key", name="uq_capture_history_owner_source"),)
    id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(Uuid, ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True)
    source_key = Column(String(64), nullable=False)
    target = Column(String(100), nullable=False)
    session_name = Column(String(240), nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=False)
    filter_name = Column(String(60), nullable=False)
    frame_count = Column(Integer, nullable=False)
    integration_seconds = Column(Float, nullable=False)
    evidence_hash = Column(String(64), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class LibrarySyncCredential(Base):
    __tablename__ = "library_sync_credentials"
    user_id = Column(Uuid, ForeignKey("profiles.user_id", ondelete="CASCADE"), primary_key=True)
    token_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
