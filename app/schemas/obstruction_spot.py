from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from app.core.obstruction_profile import ObstructionProfile


class SpotWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    profile: ObstructionProfile
    # Photo estimates reserved in storage, not accepted until capture/review exists.
    source_quality: Literal["manual_measured", "synthetic"]
    reviewed: StrictBool
    expected_revision: int | None = Field(default=None, ge=1, strict=True)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError("Name a telescope setup spot")
        return value.strip()

    @field_validator("reviewed")
    @classmethod
    def reviewed_required(cls, value):
        if not value:
            raise ValueError("Review this complete survey for the exact setup spot")
        return value
