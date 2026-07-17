from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture
from app.models import CaptureAnalysis
from app.models import ObservingSession
from app.schemas.system import SystemStatusResponse
from app.services.capture_sync_service import inspect_capture_library

router = APIRouter(prefix="/system", tags=["System"])


def get_capture_library_health(db) -> dict:
    try:
        report = inspect_capture_library(db=db)
    except OSError as error:
        return {
            "available": False,
            "clean": False,
            "library_root": "",
            "database_capture_count": 0,
            "library_fits_count": 0,
            "matched_count": 0,
            "orphan_count": 0,
            "missing_asset_count": 0,
            "conflict_count": 0,
            "status": "Unavailable",
            "message": str(error),
        }

    return {
        "available": True,
        "clean": report["clean"],
        "library_root": report["library_root"],
        "database_capture_count": report["database_capture_count"],
        "library_fits_count": report["library_fits_count"],
        "matched_count": report["matched_count"],
        "orphan_count": report["orphan_count"],
        "missing_asset_count": report["missing_asset_count"],
        "conflict_count": report["conflict_count"],
        "status": "Healthy" if report["clean"] else "Attention Required",
        "message": None,
    }


def build_system_status(db) -> dict:
    capture_count = db.query(Capture).count()
    session_count = db.query(ObservingSession).count()
    analysis_count = db.query(CaptureAnalysis).count()

    target_count = (
        db.query(Capture.object_name)
        .filter(Capture.object_name.isnot(None))
        .filter(Capture.object_name != "")
        .distinct()
        .count()
    )
    library_health = get_capture_library_health(db)
    status = (
        "Healthy"
        if library_health["clean"]
        else "Attention Required"
    )

    return {
        "project": "Project Polaris",
        "version": "1.1.0",
        "database_version": 1,
        "captures": capture_count,
        "targets": target_count,
        "sessions": session_count,
        "analysis_records": analysis_count,
        "capture_library": library_health,
        "status": status,
    }


@router.get("", response_model=SystemStatusResponse)
def system_status():
    db = SessionLocal()

    try:
        return build_system_status(db)
    finally:
        db.close()
