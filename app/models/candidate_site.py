from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String

from app.database.database import Base


class CandidateSite(Base):
    """A voluntarily saved potential observing location."""

    __tablename__ = "candidate_sites"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    bortle_class = Column(Integer, nullable=True)
    access_hours = Column(String, nullable=True)
    vehicle_requirement = Column(String, nullable=True)
    property_access = Column(String, nullable=True)
    parking_setup_confirmed = Column(Boolean, nullable=False, default=False)
    horizon_confirmed = Column(Boolean, nullable=False, default=False)
    access_confirmed = Column(Boolean, nullable=False, default=False)
    amenities_confirmed = Column(Boolean, nullable=False, default=False)
    notes = Column(String, nullable=False, default="")
    source_url = Column(String, nullable=True)
    visited_at = Column(DateTime, nullable=True)
    star_rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
