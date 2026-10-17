from pydantic import BaseModel
from typing import Optional


class DarknessSummary(BaseModel):
    sunset: Optional[str] = None
    astronomical_darkness_start: Optional[str] = None
    astronomical_darkness_end: Optional[str] = None
    astronomical_darkness_start_at: Optional[str] = None
    astronomical_darkness_end_at: Optional[str] = None
