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
    setup_minutes: int
    imaging_minutes: int
    planner_score: float
    reason: str
    recommended_sub_exposure_seconds: Optional[int] = None
    recommended_gain: Optional[float] = None
    recommended_filter: Optional[str] = None
    recommendation_source: str
    planned_subframes: Optional[int] = None
    setup_changes: List[str]


class TonightScheduleResponse(BaseModel):
    date: str
    decision: str
    advisory_only: bool = True
    blocks: List[ScheduledImagingBlock]
    allocated_minutes: int
    unscheduled_dark_minutes: int
    weather: WeatherSummary
    moon: MoonSummary
    darkness: DarknessSummary
    notes: List[str]
    fallback_target: Optional[str] = None
