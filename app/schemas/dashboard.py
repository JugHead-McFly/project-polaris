from typing import List, Optional

from pydantic import BaseModel

from app.schemas.target import RecommendedSettings


class DashboardMetrics(BaseModel):
    captures: int
    targets: int
    sessions: int
    sessions_with_captures: int
    analysis_records: int
    total_integration_seconds: int
    total_integration_hours: float


class DashboardImage(BaseModel):
    preview_url: str
    object: Optional[str] = None
    common_name: Optional[str] = None
    observation_utc: Optional[str] = None
    total_integration_seconds: int
    sub_exposure_seconds: Optional[int] = None
    subframe_count: Optional[int] = None
    gain: Optional[float] = None
    filter_name: Optional[str] = None
    quality_score: Optional[int] = None
    quality_recommendation: Optional[str] = None


class DashboardQualityComponents(BaseModel):
    base_points: int
    stars_detected: Optional[int] = None
    star_points: int
    background_level: Optional[float] = None
    background_points: int
    background_variation: Optional[float] = None
    variation_points: int
    trailing_detected: Optional[bool] = None
    trailing_points: int


class DashboardQualityCapture(DashboardImage):
    components: DashboardQualityComponents


class DashboardTargetProfile(BaseModel):
    object_type: str
    distance: str
    age: str
    summary: str
    story: Optional[str] = None
    wow_fact: Optional[str] = None
    color_note: str
    source_url: str


class DashboardTarget(BaseModel):
    object: str
    common_name: Optional[str] = None
    profile: Optional[DashboardTargetProfile] = None
    preview_url: Optional[str] = None
    preview_image: Optional[DashboardImage] = None
    capture_count: int
    session_count: int
    total_integration_seconds: int
    total_integration_hours: float
    best_quality: Optional[int] = None
    average_quality: Optional[float] = None
    scored_capture_count: int
    latest_capture: Optional[str] = None
    recommended_settings: RecommendedSettings
    status: str
    progress_percent: float
    portfolio_level: str
    current_hours: float
    goal_hours: float
    integration_goal_note: str
    remaining_hours: float
    readiness_score: int
    quality_captures: List[DashboardQualityCapture]


class DashboardCapture(BaseModel):
    polaris_id: str
    preview_url: Optional[str] = None
    object: Optional[str] = None
    common_name: Optional[str] = None
    filename: Optional[str] = None
    observation_utc: Optional[str] = None
    status: Optional[str] = None
    session_id: Optional[str] = None
    location: Optional[str] = None
    observatory: Optional[str] = None
    bortle_class: Optional[int] = None
    total_integration_seconds: int
    total_integration_hours: float
    sub_exposure_seconds: Optional[int] = None
    subframe_count: Optional[int] = None
    gain: Optional[float] = None
    filter_name: Optional[str] = None
    quality_score: Optional[int] = None
    quality_recommendation: Optional[str] = None
    components: Optional[DashboardQualityComponents] = None


class DashboardSession(BaseModel):
    session_id: str
    date: Optional[str] = None
    started_at: Optional[str] = None
    location: Optional[str] = None
    observatory: Optional[str] = None
    bortle_class: Optional[int] = None
    capture_count: int
    total_integration_seconds: int
    total_integration_hours: float
    targets: List[str]
    target_labels: List[str]
    target_common_names: List[Optional[str]]
    total_subframes: Optional[int] = None
    sub_exposure_seconds: Optional[int] = None
    gain: Optional[float] = None
    filter_name: Optional[str] = None
    average_quality: Optional[float] = None
    images: List[DashboardImage]


class DashboardCaptureLocation(BaseModel):
    location: str
    city_label: str
    latitude: float
    longitude: float
    capture_count: int
    bortle_class: Optional[int] = None


class DashboardResponse(BaseModel):
    api_version: str
    generated_at: str
    metrics: DashboardMetrics
    targets: List[DashboardTarget]
    capture_locations: List[DashboardCaptureLocation]
    recent_captures: List[DashboardCapture]
    recent_sessions: List[DashboardSession]
