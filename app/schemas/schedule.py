from typing import List, Optional

from pydantic import BaseModel

from app.schemas.darkness import DarknessSummary
from app.schemas.moon import MoonSummary
from app.schemas.weather import WeatherSummary


class ScheduledImagingBlock(BaseModel):
    object: str
    start: str
    end: str
    duration_minutes: int
    planner_score: float
    reason: str


class TonightScheduleResponse(BaseModel):
    date: str
    decision: str
    advisory_only: bool = True
    blocks: List[ScheduledImagingBlock]
    weather: WeatherSummary
    moon: MoonSummary
    darkness: DarknessSummary
    notes: List[str]
    fallback_target: Optional[str] = None
