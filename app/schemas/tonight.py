from typing import List, Optional

from pydantic import BaseModel

from app.schemas.darkness import DarknessSummary
from app.schemas.moon import MoonSummary
from app.schemas.night_rating import NightRating
from app.schemas.observatory import ObservatorySummary
from app.schemas.schedule import TonightScheduleResponse
from app.schemas.target import TargetSummary
from app.schemas.weather import WeatherSummary


class NightPlanTarget(BaseModel):
    object: str
    start: Optional[str] = None
    end: Optional[str] = None
    reason: Optional[str] = None


class NightPlan(BaseModel):
    decision: str
    overall_rating: int
    start_imaging: Optional[str] = None
    shutdown_time: Optional[str] = None
    target_sequence: List[NightPlanTarget]
    backup_option: Optional[NightPlanTarget] = None
    notes: List[str]


class TonightResponse(BaseModel):
    date: str
    observatory: ObservatorySummary
    recommended_target: Optional[TargetSummary] = None
    backup_target: Optional[TargetSummary] = None
    moon: MoonSummary
    weather: WeatherSummary
    night_rating: NightRating
    message: str
    night_plan: NightPlan
    darkness: DarknessSummary
    schedule: TonightScheduleResponse
