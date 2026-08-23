from typing import List, Optional
from uuid import UUID

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


class OpportunityScoreComponent(BaseModel):
    key: str
    label: str
    description: str
    points: Optional[float] = None
    max: float
    source: str
    detail_title: Optional[str] = None
    detail: Optional[str] = None


class OpportunityScore(BaseModel):
    total: float
    components: List[OpportunityScoreComponent]


class DewRiskGuidance(BaseModel):
    level: str
    label: str
    summary: str
    action: str
    temperature_f: Optional[float] = None
    dew_point_f: Optional[float] = None
    spread_f: Optional[float] = None
    forecast_at: Optional[str] = None


class ConditionsTrend(BaseModel):
    direction: str
    label: str
    message: str
    basis: Optional[str] = None
    forecast_start: Optional[str] = None
    forecast_end: Optional[str] = None


class TonightResponse(BaseModel):
    recommendation_run_id: Optional[UUID] = None
    date: str
    observatory: ObservatorySummary
    recommended_target: Optional[TargetSummary] = None
    backup_target: Optional[TargetSummary] = None
    moon: MoonSummary
    weather: WeatherSummary
    night_rating: NightRating
    opportunity_score: OpportunityScore
    dew_risk: DewRiskGuidance
    conditions_trend: ConditionsTrend
    message: str
    night_plan: NightPlan
    darkness: DarknessSummary
    schedule: TonightScheduleResponse
