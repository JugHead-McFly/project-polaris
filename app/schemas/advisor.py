from typing import Optional

from pydantic import BaseModel


class ExposureAdvisorResponse(BaseModel):
    object: str
    status: str

    current_integration_seconds: int
    current_integration_hours: float

    goal_hours: float
    remaining_seconds: int
    remaining_hours: float

    recommended_sub_exposure_seconds: Optional[int] = None
    recommended_gain: Optional[float] = None
    recommended_filter: Optional[str] = None

    additional_subframes_needed: Optional[int] = None

    recommendation_source: str
    source_capture_id: Optional[str] = None
    confidence: int

    recommendation: str