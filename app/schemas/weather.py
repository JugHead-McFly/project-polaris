from typing import Optional

from pydantic import BaseModel


class WeatherSummary(BaseModel):
    postal_code: str
    temperature_f: Optional[float] = None
    cloud_cover_percent: Optional[int] = None
    humidity_percent: Optional[int] = None
    dew_point_f: Optional[float] = None
    wind_speed_mph: Optional[float] = None
    seeing: Optional[str] = None
    transparency: Optional[str] = None
    observing_rating: int
    status: str
    observed_at: Optional[str] = None
    fetched_at: Optional[str] = None
