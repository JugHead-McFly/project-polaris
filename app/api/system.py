from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture
from app.models import CaptureAnalysis
from app.models import ObservingSession

router = APIRouter(prefix="/system", tags=["System"])


@router.get("")
def system_status():
    db = SessionLocal()

    try:
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

        return {
            "project": "Project Polaris",
            "version": "1.1.0",
            "database_version": 1,
            "captures": capture_count,
            "targets": target_count,
            "sessions": session_count,
            "analysis_records": analysis_count,
            "status": "Healthy",
        }

    finally:
        db.close()