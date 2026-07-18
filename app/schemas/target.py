from typing import List, Optional

from pydantic import BaseModel


class RecommendedExposure(BaseModel):
    exposure_seconds: int
    gain: int
    goal_subframes: int


class RecommendedSettings(BaseModel):
    source: str
    polaris_id: Optional[str] = None
    exposure_seconds: Optional[int] = None
    gain: Optional[float] = None
    filter_name: Optional[str] = None


class TargetCaptureSummary(BaseModel):
    polaris_id: str
    filename: str
    observation_utc: Optional[str] = None
    status: Optional[str] = None

    sub_exposure_seconds: Optional[int] = None
    subframe_count: Optional[int] = None
    total_integration_seconds: Optional[int] = None
    total_integration_hours: Optional[float] = None

    gain: Optional[float] = None
    filter_name: Optional[str] = None
    quality_score: Optional[int] = None


class TargetSummary(BaseModel):
    object: str
    common_name: Optional[str] = None

    capture_count: int
    session_count: int

    total_integration_seconds: int
    total_integration_hours: float

    best_quality: Optional[int] = None
    average_quality: Optional[float] = None
    latest_capture: Optional[str] = None

    recommended_settings: RecommendedSettings

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

    captures: List[TargetCaptureSummary]
