from typing import List, Optional

from pydantic import BaseModel

from app.schemas.advisor import ExposureAdvisorResponse
from app.schemas.darkness import DarknessSummary
from app.schemas.moon import MoonSummary
from app.schemas.weather import WeatherSummary


class PlannerTarget(BaseModel):
    advisor: ExposureAdvisorResponse

    planner_score: float
    observable: bool

    current_altitude: Optional[float] = None
    altitude_at_dark_midpoint: Optional[float] = None
    maximum_dark_altitude: Optional[float] = None
    average_dark_altitude: Optional[float] = None

    usable_dark_minutes: int
    usable_dark_hours: float

    transit_time: Optional[str] = None
    recommended_start: Optional[str] = None
    recommended_end: Optional[str] = None

    moon_separation_degrees: Optional[float] = None
    moon_warning: Optional[str] = None

    selection_reason: str


class TonightPlannerResponse(BaseModel):
    recommended_target: Optional[PlannerTarget] = None
    best_theoretical_target: Optional[PlannerTarget] = None
    alternatives: List[PlannerTarget]

    weather: WeatherSummary
    moon: MoonSummary
    darkness: DarknessSummary

    decision: str
    notes: List[str]