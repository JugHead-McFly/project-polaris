from typing import Optional

from pydantic import BaseModel


class WeatherSummary(BaseModel):
    postal_code: Optional[str] = None
    temperature_f: Optional[float] = None
    planned_temperature_f: Optional[float] = None
    planned_temperature_at: Optional[str] = None
    planned_cloud_cover_percent: Optional[int] = None
    planned_humidity_percent: Optional[int] = None
    planned_dew_point_f: Optional[float] = None
    planned_wind_speed_mph: Optional[float] = None
    cloud_cover_percent: Optional[int] = None
    humidity_percent: Optional[int] = None
    dew_point_f: Optional[float] = None
    wind_speed_mph: Optional[float] = None
    seeing: Optional[str] = None
    seeing_index: Optional[int] = None
    seeing_forecast_at: Optional[str] = None
    planned_seeing_index: Optional[int] = None
    planned_seeing_forecast_at: Optional[str] = None
    transparency: Optional[str] = None
    transparency_index: Optional[int] = None
    transparency_forecast_at: Optional[str] = None
    planned_transparency_index: Optional[int] = None
    planned_transparency_forecast_at: Optional[str] = None
    astro_forecast_provider: Optional[str] = None
    astro_forecast_status: Optional[str] = None
    astro_forecast_fetched_at: Optional[str] = None
    observing_rating: int
    status: str
    observed_at: Optional[str] = None
    fetched_at: Optional[str] = None
