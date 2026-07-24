from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CaptureAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    capture_id: int
    stars_detected: Optional[int] = None
    median_fwhm: Optional[float] = None
    eccentricity: Optional[float] = None
    median_roundness: Optional[float] = None
    median_sharpness: Optional[float] = None
    background_level: Optional[float] = None
    background_noise: Optional[float] = None
    relative_background_noise: Optional[float] = None
    background_gradient: Optional[float] = None
    clipped_pixel_fraction: Optional[float] = None
    snr: Optional[float] = None
    star_sample_count: Optional[int] = None
    trailing_detected: Optional[bool] = None
    quality_score: Optional[int] = None
    legacy_quality_score: Optional[int] = None
    scoring_version: Optional[str] = None
    analysis_confidence: Optional[str] = None
    recommendation: Optional[str] = None
    created_at: datetime
