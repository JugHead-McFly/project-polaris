from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey

from app.database.database import Base


class Capture(Base):
    __tablename__ = "captures"

    id = Column(Integer, primary_key=True)

    polaris_id = Column(String, unique=True, index=True)
    session_id = Column(
    Integer,
    ForeignKey("sessions.id"),
    nullable=True,
    )   
    object_name = Column(String)
    filename = Column(String)
    asset_path = Column(String)

    observation_utc = Column(String)

    gain = Column(Float)
    ra = Column(Float)
    dec = Column(Float)

    telescope = Column(String)
    firmware = Column(String)

    status = Column(String, default="Raw")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)