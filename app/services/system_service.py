from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.diagnostics import get_service_diagnostics
from app.core.diagnostics import get_uptime_seconds
from app.models import Capture
from app.models import CaptureAnalysis
from app.models import ObservingSession
from app.services.capture_sync_service import inspect_capture_library


CURRENT_DATA_HOURS = 24
STALE_DATA_HOURS = 30 * 24


def _parse_datetime(value) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _latest_datetime(values: Iterable) -> Optional[datetime]:
    parsed_values = [
        parsed
        for value in values
        if (parsed := _parse_datetime(value)) is not None
    ]
    return max(parsed_values) if parsed_values else None


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def build_data_freshness(
    captures: list,
    sessions: list,
    analyses: list,
    now: Optional[datetime] = None,
) -> dict:
    checked_at = _parse_datetime(now) or datetime.now(timezone.utc)
    latest_observation = _latest_datetime(
        capture.observation_utc
        for capture in captures
    )
    latest_database_update = _latest_datetime(
        capture.updated_at
        for capture in captures
    )
    latest_session_update = _latest_datetime(
        session.updated_at
        for session in sessions
    )
    latest_analysis = _latest_datetime(
        analysis.created_at
        for analysis in analyses
    )

    capture_age_hours = None
    status = "Empty"

    if latest_observation is not None:
        raw_capture_age_hours = max(
            (checked_at - latest_observation).total_seconds() / 3600,
            0,
        )
        capture_age_hours = round(raw_capture_age_hours, 1)
        if raw_capture_age_hours <= CURRENT_DATA_HOURS:
            status = "Current"
        elif raw_capture_age_hours <= STALE_DATA_HOURS:
            status = "Recent"
        else:
            status = "Stale"

    return {
        "status": status,
        "latest_capture_observation_utc": _iso(latest_observation),
        "capture_age_hours": capture_age_hours,
        "latest_database_update_utc": _iso(latest_database_update),
        "latest_session_update_utc": _iso(latest_session_update),
        "latest_analysis_utc": _iso(latest_analysis),
    }


def get_capture_library_health(db: Session) -> dict:
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


def build_system_status(db: Session) -> dict:
    checked_at = datetime.now(timezone.utc)
    captures = db.query(Capture).all()
    sessions = db.query(ObservingSession).all()
    analyses = db.query(CaptureAnalysis).all()
    target_count = len(
        {
            capture.object_name.strip().upper()
            for capture in captures
            if capture.object_name and capture.object_name.strip()
        }
    )
    library_health = get_capture_library_health(db)
    data_freshness = build_data_freshness(
        captures=captures,
        sessions=sessions,
        analyses=analyses,
        now=checked_at,
    )
    services = get_service_diagnostics()

    if not library_health["clean"]:
        status = "Attention Required"
    elif data_freshness["status"] in {"Empty", "Stale"}:
        status = "Degraded"
    elif any(service["status"] == "Degraded" for service in services):
        status = "Degraded"
    else:
        status = "Healthy"

    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database_version": 1,
        "captures": len(captures),
        "targets": target_count,
        "sessions": len(sessions),
        "analysis_records": len(analyses),
        "capture_library": library_health,
        "diagnostics": {
            "checked_at": checked_at.isoformat(),
            "uptime_seconds": get_uptime_seconds(),
            "database_status": "Healthy",
            "data_freshness": data_freshness,
            "services": services,
        },
        "status": status,
    }
