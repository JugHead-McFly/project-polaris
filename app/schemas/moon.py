from typing import Optional

from pydantic import BaseModel


class MoonSummary(BaseModel):
    illumination_percent: float
    phase_name: Optional[str] = None
    altitude_degrees: float
    above_horizon: bool
    next_moonrise: Optional[str] = None
    next_moonset: Optional[str] = None
