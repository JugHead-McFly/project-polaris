from typing import Optional

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


class SystemStatusResponse(BaseModel):
    project: str
    version: str
    database_version: int
    captures: int
    targets: int
    sessions: int
    analysis_records: int
    capture_library: CaptureLibraryHealth
    status: str
