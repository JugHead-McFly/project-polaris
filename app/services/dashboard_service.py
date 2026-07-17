from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Capture
from app.models import CaptureAnalysis
from app.models import ObservingSession
from app.services.portfolio_service import build_portfolio_target
from app.services.target_service import get_capture_integration_seconds
from app.services.target_service import get_latest_analysis_by_capture
from app.services.target_service import get_recommended_settings


RECENT_CAPTURE_LIMIT = 8
RECENT_SESSION_LIMIT = 6


def _build_target_history(
    object_name: str,
    captures: List[Capture],
    analyses_by_capture: Dict[int, CaptureAnalysis],
) -> Dict:
    total_seconds = sum(
        get_capture_integration_seconds(capture)
        for capture in captures
    )
    total_hours = round(total_seconds / 3600, 2)
    portfolio = build_portfolio_target(
        object_name=object_name,
        total_hours=total_hours,
    )
    quality_scores = [
        analysis.quality_score
        for capture in captures
        if (
            (analysis := analyses_by_capture.get(capture.id))
            is not None
            and analysis.quality_score is not None
        )
    ]
    latest_capture = max(
        captures,
        key=lambda capture: (
            capture.observation_utc or "",
            capture.id,
        ),
    )

    return {
        "object": object_name,
        "capture_count": len(captures),
        "session_count": len(
            {
                capture.session_id
                for capture in captures
                if capture.session_id is not None
            }
        ),
        "total_integration_seconds": total_seconds,
        "total_integration_hours": total_hours,
        "best_quality": max(quality_scores) if quality_scores else None,
        "average_quality": (
            round(sum(quality_scores) / len(quality_scores), 1)
            if quality_scores
            else None
        ),
        "latest_capture": latest_capture.observation_utc,
        "recommended_settings": get_recommended_settings(
            captures=captures,
            analyses_by_capture=analyses_by_capture,
        ),
        "status": portfolio["status"],
        "progress_percent": portfolio["progress_percent"],
        "portfolio_level": portfolio["portfolio_level"],
        "current_hours": portfolio["current_hours"],
        "goal_hours": portfolio["goal_hours"],
        "remaining_hours": portfolio["remaining_hours"],
        "readiness_score": portfolio["readiness_score"],
    }


def _build_recent_capture(
    capture: Capture,
    analyses_by_capture: Dict[int, CaptureAnalysis],
    session_names: Dict[int, str],
) -> Dict:
    integration_seconds = get_capture_integration_seconds(capture)
    analysis = analyses_by_capture.get(capture.id)

    return {
        "polaris_id": capture.polaris_id,
        "object": capture.object_name,
        "filename": capture.filename,
        "observation_utc": capture.observation_utc,
        "status": capture.status,
        "session_id": session_names.get(capture.session_id),
        "total_integration_seconds": integration_seconds,
        "total_integration_hours": round(integration_seconds / 3600, 2),
        "sub_exposure_seconds": capture.sub_exposure_seconds,
        "subframe_count": capture.subframe_count,
        "gain": capture.gain,
        "filter_name": capture.filter_name,
        "quality_score": (
            analysis.quality_score
            if analysis is not None
            else None
        ),
    }


def _build_recent_session(
    session: ObservingSession,
    captures: List[Capture],
) -> Dict:
    total_seconds = sum(
        get_capture_integration_seconds(capture)
        for capture in captures
    )

    return {
        "session_id": session.session_id,
        "date": session.date,
        "location": session.location,
        "observatory": session.observatory,
        "capture_count": len(captures),
        "total_integration_seconds": total_seconds,
        "total_integration_hours": round(total_seconds / 3600, 2),
        "targets": sorted(
            {
                capture.object_name
                for capture in captures
                if capture.object_name
            }
        ),
    }


def build_dashboard_response(db: Session) -> Dict:
    captures = (
        db.query(Capture)
        .order_by(Capture.id.desc())
        .all()
    )
    sessions = (
        db.query(ObservingSession)
        .order_by(ObservingSession.id.desc())
        .all()
    )
    capture_ids = [capture.id for capture in captures]
    analyses_by_capture = get_latest_analysis_by_capture(
        db=db,
        capture_ids=capture_ids,
    )
    analysis_records = db.query(CaptureAnalysis).count()

    captures_by_target = defaultdict(list)
    captures_by_session = defaultdict(list)
    for capture in captures:
        if capture.object_name:
            captures_by_target[capture.object_name.strip().upper()].append(
                capture
            )
        if capture.session_id is not None:
            captures_by_session[capture.session_id].append(capture)

    targets = [
        _build_target_history(
            object_name=object_name,
            captures=target_captures,
            analyses_by_capture=analyses_by_capture,
        )
        for object_name, target_captures in captures_by_target.items()
    ]
    targets.sort(
        key=lambda target: (
            -target["readiness_score"],
            target["object"],
        )
    )

    session_names = {
        session.id: session.session_id
        for session in sessions
    }
    total_integration_seconds = sum(
        get_capture_integration_seconds(capture)
        for capture in captures
    )

    return {
        "api_version": settings.VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "captures": len(captures),
            "targets": len(captures_by_target),
            "sessions": len(sessions),
            "analysis_records": analysis_records,
            "total_integration_seconds": total_integration_seconds,
            "total_integration_hours": round(
                total_integration_seconds / 3600,
                2,
            ),
        },
        "targets": targets,
        "recent_captures": [
            _build_recent_capture(
                capture=capture,
                analyses_by_capture=analyses_by_capture,
                session_names=session_names,
            )
            for capture in captures[:RECENT_CAPTURE_LIMIT]
        ],
        "recent_sessions": [
            _build_recent_session(
                session=session,
                captures=captures_by_session.get(session.id, []),
            )
            for session in sessions[:RECENT_SESSION_LIMIT]
        ],
    }
