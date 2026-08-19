from typing import List

from pydantic import BaseModel


class RigProfileSummaryResponse(BaseModel):
    key: str
    label: str
    manufacturer: str
    has_field_of_view: bool
    has_battery_limit: bool
    has_storage_limit: bool
    has_temperature_limit: bool
    has_frame_limit: bool
    confidence: str


class RigProfileCatalogResponse(BaseModel):
    total_profiles: int
    manufacturers: List[str]
    profiles_with_field_of_view: int
    profiles_with_battery_limit: int
    profiles_with_storage_limit: int
    profiles_with_temperature_limit: int
    profiles_with_frame_limit: int
    profiles: List[RigProfileSummaryResponse]
