from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from app.database.database import Base


class CaptureAnalysis(Base):
    __tablename__ = "capture_analyses"

    id = Column(Integer, primary_key=True, index=True)

    capture_id = Column(
        Integer,
        ForeignKey("captures.id"),
        nullable=False,
        index=True,
    )

    stars_detected = Column(Integer, nullable=True)
    median_fwhm = Column(Float, nullable=True)
    eccentricity = Column(Float, nullable=True)
    background_level = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)
    trailing_detected = Column(Boolean, nullable=True)

    quality_score = Column(Integer, nullable=True)
    recommendation = Column(String, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )