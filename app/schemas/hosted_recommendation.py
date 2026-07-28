from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class RecommendationFeedbackUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    useful: bool
    reason: Optional[str] = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class RecommendationFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recommendation_run_id: UUID
    useful: bool
    reason: Optional[str]
    created_at: datetime
