from pydantic import BaseModel


class ObservatorySummary(BaseModel):
    name: str
    postal_code: str
    timezone: str
    latitude: float
    longitude: float
    elevation_meters: float