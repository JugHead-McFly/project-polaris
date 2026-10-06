import re
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_target(value: str) -> str:
    value = value.strip().upper()
    match = re.fullmatch(r"(M|NGC|IC|C)\s*(\d+)", value)
    if match:
        prefix, number = match.groups()
        value = f"C {int(number)}" if prefix == "C" else f"{prefix}{int(number)}"
    return {"NGC7000": "C 20", "NORTH AMERICA NEBULA": "C 20"}.get(value, value)


class CaptureSessionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    source_key: str = Field(pattern=r"^[a-f0-9]{64}$")
    target: str = Field(min_length=1, max_length=100)
    session_name: str = Field(min_length=1, max_length=240)
    captured_at: datetime
    filter_name: str = Field(min_length=1, max_length=60)
    frame_count: int = Field(gt=0, le=100000)
    integration_seconds: float = Field(gt=0, le=604800)
    evidence_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("target")
    @classmethod
    def target_name(cls, value):
        return normalize_target(value)

    @field_validator("captured_at")
    @classmethod
    def aware_date(cls, value):
        if value.tzinfo is None or value > datetime.now(timezone.utc):
            raise ValueError("Capture time must be timezone-aware and in the past")
        return value


class CaptureManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    basis: Literal["verified_raw_frames"] = "verified_raw_frames"
    sessions: list[CaptureSessionSummary] = Field(max_length=2000)
