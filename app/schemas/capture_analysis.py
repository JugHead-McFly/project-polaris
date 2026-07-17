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
    background_level: Optional[float] = None
    snr: Optional[float] = None
    trailing_detected: Optional[bool] = None
    quality_score: Optional[int] = None
    recommendation: Optional[str] = None
    created_at: datetime
