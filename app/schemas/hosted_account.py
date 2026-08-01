from datetime import datetime
from typing import Literal
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


TrackingPreference = Literal[
    "not_sure",
    "alt_az",
    "equatorial",
    "both",
]


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: Optional[str] = Field(
        default=None,
        max_length=100,
    )
    onboarding_state: str = Field(
        default="not_started",
        min_length=1,
        max_length=30,
    )


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    display_name: Optional[str]
    onboarding_state: str
    created_at: datetime
    updated_at: datetime


class ObservatoryFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    coordinates_are_approximate: bool = True
    elevation_m: Optional[float] = Field(
        default=None,
        ge=-500,
        le=9000,
    )
    timezone_name: str = Field(min_length=1, max_length=64)
    bortle_class: Optional[int] = Field(default=None, ge=1, le=9)
    telescope_model: Optional[str] = Field(default=None, max_length=100)
    tracking_preference: TrackingPreference = "not_sure"

    @field_validator("timezone_name")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                "timezone_name must be an IANA timezone."
            ) from error
        return value


class ObservatoryCreate(ObservatoryFields):
    pass


class ObservatoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    coordinates_are_approximate: Optional[bool] = None
    elevation_m: Optional[float] = Field(
        default=None,
        ge=-500,
        le=9000,
    )
    timezone_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    bortle_class: Optional[int] = Field(default=None, ge=1, le=9)
    telescope_model: Optional[str] = Field(default=None, max_length=100)
    tracking_preference: Optional[TrackingPreference] = None

    @field_validator("timezone_name")
    @classmethod
    def timezone_must_exist(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                "timezone_name must be an IANA timezone."
            ) from error
        return value


class ObservatoryResponse(ObservatoryFields):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID
    created_at: datetime
    updated_at: datetime
