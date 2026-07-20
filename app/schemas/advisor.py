from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.target import IntegrationGoalOption


class ExposureAdvisorResponse(BaseModel):
    object: str
    status: str

    current_integration_seconds: int
    current_integration_hours: float

    goal_hours: float
    goal_tier: str = "detailed"
    goal_source: str = "Polaris target-class starter"
    goal_options: List[IntegrationGoalOption] = Field(default_factory=list)
    goal_factors: List[str] = Field(default_factory=list)
    integration_goal_note: str = ""
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
