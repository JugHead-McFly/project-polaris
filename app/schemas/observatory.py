from typing import Optional

from pydantic import BaseModel


class ObservatorySummary(BaseModel):
    name: str
    postal_code: Optional[str] = None
    timezone: str
    latitude: float
    longitude: float
    elevation_meters: float
    rig_profile_key: Optional[str] = None
    rig_profile_label: Optional[str] = None
