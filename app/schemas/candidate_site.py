from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class CandidateSiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    bortle_class: Optional[int] = Field(default=None, ge=1, le=9)
    access_hours: Optional[str] = Field(default=None, max_length=250)
    vehicle_requirement: Optional[str] = Field(default=None, max_length=80)
    property_access: Optional[str] = Field(default=None, max_length=80)
    parking_setup_confirmed: bool = False
    horizon_confirmed: bool = False
    access_confirmed: bool = False
    amenities_confirmed: bool = False
    notes: str = Field(default="", max_length=1000)
    source_url: Optional[str] = Field(default=None, max_length=500)


class CandidateSiteResponse(CandidateSiteCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    visited_at: Optional[datetime] = None
    star_rating: Optional[int] = Field(default=None, ge=1, le=5)


class CandidateSiteUpdate(BaseModel):
    visited: Optional[bool] = None
    star_rating: Optional[int] = Field(default=None, ge=1, le=5)
    access_hours: Optional[str] = Field(default=None, max_length=250)
    vehicle_requirement: Optional[str] = Field(default=None, max_length=80)
    property_access: Optional[str] = Field(default=None, max_length=80)
    parking_setup_confirmed: Optional[bool] = None
    horizon_confirmed: Optional[bool] = None
    access_confirmed: Optional[bool] = None
    amenities_confirmed: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
