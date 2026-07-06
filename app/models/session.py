from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app.database.database import Base


class ObservingSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)

    session_id = Column(String, unique=True, index=True)

    date = Column(String)
    location = Column(String)
    observatory = Column(String)

    moon_phase = Column(String)
    weather_summary = Column(String)
    notes = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)