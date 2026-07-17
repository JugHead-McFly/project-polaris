from typing import List, Optional

from pydantic import BaseModel

from app.schemas.target import RecommendedSettings


class DashboardMetrics(BaseModel):
    captures: int
    targets: int
    sessions: int
    analysis_records: int
    total_integration_seconds: int
    total_integration_hours: float


class DashboardTarget(BaseModel):
    object: str
    capture_count: int
    session_count: int
    total_integration_seconds: int
    total_integration_hours: float
    best_quality: Optional[int] = None
    average_quality: Optional[float] = None
    latest_capture: Optional[str] = None
    recommended_settings: RecommendedSettings
    status: str
    progress_percent: float
    portfolio_level: str
    current_hours: float
    goal_hours: float
    remaining_hours: float
    readiness_score: int


class DashboardCapture(BaseModel):
    polaris_id: str
    object: Optional[str] = None
    filename: Optional[str] = None
    observation_utc: Optional[str] = None
    status: Optional[str] = None
    session_id: Optional[str] = None
    total_integration_seconds: int
    total_integration_hours: float
    sub_exposure_seconds: Optional[int] = None
    subframe_count: Optional[int] = None
    gain: Optional[float] = None
    filter_name: Optional[str] = None
    quality_score: Optional[int] = None


class DashboardSession(BaseModel):
    session_id: str
    date: Optional[str] = None
    location: Optional[str] = None
    observatory: Optional[str] = None
    capture_count: int
    total_integration_seconds: int
    total_integration_hours: float
    targets: List[str]


class DashboardResponse(BaseModel):
    api_version: str
    generated_at: str
    metrics: DashboardMetrics
    targets: List[DashboardTarget]
    recent_captures: List[DashboardCapture]
    recent_sessions: List[DashboardSession]
