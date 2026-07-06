from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CaptureSummary(BaseModel):
    polaris_id: str
    object_name: Optional[str] = None
    filename: Optional[str] = None
    status: Optional[str] = None
    observation_utc: Optional[str] = None


class CaptureDetail(CaptureSummary):
    id: int
    asset_path: Optional[str] = None
    gain: Optional[float] = None
    ra: Optional[float] = None
    dec: Optional[float] = None
    telescope: Optional[str] = None
    firmware: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None