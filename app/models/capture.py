from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String

from app.database.database import Base


class Capture(Base):
    __tablename__ = "captures"

    id = Column(Integer, primary_key=True)

    object_name = Column(String)
    filename = Column(String)
    observation_utc = Column(String)
    gain = Column(Float)
    ra = Column(Float)
    dec = Column(Float)
    telescope = Column(String)
    firmware = Column(String)
