from typing import List, Optional, Tuple

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


class RigProfileDetailResponse(BaseModel):
    key: str
    manufacturer: str
    model: str
    aperture_mm: Optional[float]
    focal_length_mm: Optional[float]
    focal_ratio: Optional[float]
    sensor_name: Optional[str]
    resolution: Optional[Tuple[int, int]]
    pixel_size_um: Optional[float]
    sensor_size_mm: Optional[Tuple[float, float]]
    native_fov_degrees: Optional[Tuple[float, float]]
    supported_exposures_seconds: Tuple[int, ...]
    default_gain: Optional[float]
    filters: Tuple[str, ...]
    mount_type: Optional[str]
    tracking_modes: Tuple[str, ...]
    frame_limit: Optional[int]
    storage_gb: Optional[float]
    battery_life_hours: Optional[float]
    dew_heater_battery_life_hours: Optional[float]
    operating_temperature_c: Optional[Tuple[float, float]]
    source_urls: Tuple[str, ...]
    confidence: str
    notes: str


class RigTargetFitResponse(BaseModel):
    rig_key: str
    target_width_degrees: Optional[float]
    target_height_degrees: Optional[float]
    fits: Optional[bool]
    label: str
    margin_degrees: Optional[float]
    reason: str
