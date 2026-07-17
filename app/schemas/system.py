from typing import List, Optional

from pydantic import BaseModel


class CaptureLibraryHealth(BaseModel):
    available: bool
    clean: bool
    library_root: str
    database_capture_count: int
    library_fits_count: int
    matched_count: int
    orphan_count: int
    missing_asset_count: int
    conflict_count: int
    status: str
    message: Optional[str] = None


class DataFreshness(BaseModel):
    status: str
    latest_capture_observation_utc: Optional[str] = None
    capture_age_hours: Optional[float] = None
    latest_database_update_utc: Optional[str] = None
    latest_session_update_utc: Optional[str] = None
    latest_analysis_utc: Optional[str] = None


class ServiceDiagnostic(BaseModel):
    service: str
    status: str
    checked_at: Optional[str] = None
    last_success_at: Optional[str] = None
    message: str


class RuntimeDiagnostics(BaseModel):
    checked_at: str
    uptime_seconds: int
    database_status: str
    data_freshness: DataFreshness
    services: List[ServiceDiagnostic]


class SystemStatusResponse(BaseModel):
    project: str
    version: str
    database_version: int
    captures: int
    targets: int
    sessions: int
    analysis_records: int
    capture_library: CaptureLibraryHealth
    diagnostics: RuntimeDiagnostics
    status: str
