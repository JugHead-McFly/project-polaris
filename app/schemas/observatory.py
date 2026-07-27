from typing import Optional

from pydantic import BaseModel


class ObservatorySummary(BaseModel):
    name: str
    postal_code: Optional[str] = None
    timezone: str
    latitude: float
    longitude: float
    elevation_meters: float
