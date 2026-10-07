from uuid import uuid4
from sqlalchemy import Column, Date, DateTime, Float, ForeignKeyConstraint, JSON, String, UniqueConstraint, Uuid
from app.database.database import Base


class NightlyForecast(Base):
    __tablename__ = "nightly_forecasts"
    __table_args__ = (
        ForeignKeyConstraint(["observatory_id", "user_id"], ["observatories.id", "observatories.user_id"], ondelete="CASCADE", name="fk_nightly_forecast_owner"),
        UniqueConstraint("observatory_id", "user_id", "night_date", name="uq_nightly_forecast_home_date"),
    )
    id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(Uuid, nullable=False, index=True)
    observatory_id = Column(Uuid, nullable=False)
    night_date = Column(Date, nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timezone_name = Column(String(64), nullable=False)
    forecasts = Column(JSON, nullable=False, default=dict)
    observation = Column(JSON, nullable=False, default=dict)
