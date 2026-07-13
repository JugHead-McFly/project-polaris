from typing import Dict, Optional

from pydantic import BaseModel


class RecommendedExposure(BaseModel):
    exposure_seconds: int
    gain: int
    goal_subframes: int


class TargetSummary(BaseModel):
    object: str
    constellation: str
    target_type: str
    difficulty: str
    recommended_filter: str
    recommended_exposure: RecommendedExposure
    season_score: int
    science_priority: int
    readiness_score: int
    status: str
    best_window: str
    progress_percent: float
    portfolio_level: str
    next_action: str
    current_hours: float
    goal_hours: float
    remaining_hours: float
    estimated_nights_remaining: float
    observable: bool
    current_altitude: Optional[float] = None
    transit_time: Optional[str] = None
    moon_warning: Optional[str] = None
    recommended_start: Optional[str] = None
    recommended_end: Optional[str] = None
    moon_separation_degrees: Optional[float] = None
    reason: Optional[str] = None