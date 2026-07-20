from collections import defaultdict
from datetime import datetime, timezone
import re
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observatory import OBSERVATORY_NAME
from app.data.targets import get_target_common_name
from app.data.targets import get_target_profile
from app.models import Capture
from app.models import CaptureAnalysis
from app.models import ObservingSession
from app.services.portfolio_service import build_portfolio_target
from app.services.capture_analysis_service import calculate_quality_components
from app.services.capture_analysis_service import build_quality_improvement_recommendation
from app.services.target_service import get_capture_integration_seconds
from app.services.target_service import get_latest_analysis_by_capture
from app.services.target_service import get_recommended_settings


RECENT_CAPTURE_LIMIT = 8
RECENT_SESSION_LIMIT = 6
QUALITY_CAPTURE_LIMIT = 12

# City centers are intentionally used for the history map.  Polaris should
# show where a capture was made without exposing a private observing address.
CAPTURE_LOCATION_COORDINATES = {
    "Gilbert, AZ 85297": {
        "city_label": "Gilbert, AZ",
        "latitude": 33.3528,
        "longitude": -111.7890,
    },
    "Huntsville, AL 35806": {
        "city_label": "Huntsville, AL",
        "latitude": 34.7304,
        "longitude": -86.5861,
    },
}


def _analysis_standard_deviation(
    analysis: Optional[CaptureAnalysis],
) -> Optional[float]:
    if analysis is None or not analysis.recommendation:
        return None

    match = re.search(
        r"\bstddev=([0-9]+(?:\.[0-9]+)?)",
        analysis.recommendation,
    )
    return float(match.group(1)) if match else None


def _parse_observation_time(value) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _capture_sort_key(capture: Capture):
    return (
        _parse_observation_time(capture.observation_utc)
        or datetime.min.replace(tzinfo=timezone.utc),
        capture.id or 0,
    )


def _session_start(captures: List[Capture]) -> Optional[datetime]:
    observation_times = [
        parsed
        for capture in captures
        if (
            parsed := _parse_observation_time(
                capture.observation_utc
            )
        ) is not None
    ]
    return min(observation_times) if observation_times else None


def _session_sort_key(
    session: ObservingSession,
    captures: List[Capture],
):
    return (
        _session_start(captures)
        or _parse_observation_time(session.date)
        or datetime.min.replace(tzinfo=timezone.utc),
        session.id or 0,
    )


def _single_value(captures: List[Capture], attribute: str):
    values = {
        getattr(capture, attribute)
        for capture in captures
        if getattr(capture, attribute) is not None
    }
    return next(iter(values)) if len(values) == 1 else None


def _target_label(object_name: str) -> str:
    common_name = get_target_common_name(object_name)
    return (
        f"{object_name} — {common_name}"
        if common_name
        else object_name
    )


def _build_dashboard_image(
    capture: Capture,
    analysis: Optional[CaptureAnalysis],
) -> Dict:
    integration_seconds = get_capture_integration_seconds(capture)
    standard_deviation = _analysis_standard_deviation(analysis)
    return {
        "preview_url": f"/operator-preview/{capture.polaris_id}",
        "object": capture.object_name,
        "common_name": get_target_common_name(capture.object_name),
        "observation_utc": capture.observation_utc,
        "total_integration_seconds": integration_seconds,
        "sub_exposure_seconds": capture.sub_exposure_seconds,
        "subframe_count": capture.subframe_count,
        "gain": capture.gain,
        "filter_name": capture.filter_name,
        "quality_score": (
            analysis.quality_score
            if analysis is not None
            else None
        ),
        "quality_recommendation": build_quality_improvement_recommendation(
            stars_detected=analysis.stars_detected if analysis is not None else None,
            median_value=analysis.background_level if analysis is not None else None,
            standard_deviation=standard_deviation,
            trailing_detected=analysis.trailing_detected if analysis is not None else None,
        ),
    }


def _build_quality_capture(
    capture: Capture,
    analysis: CaptureAnalysis,
) -> Dict:
    standard_deviation = _analysis_standard_deviation(analysis)
    components = calculate_quality_components(
        stars_detected=analysis.stars_detected,
        median_value=analysis.background_level,
        standard_deviation=standard_deviation,
        trailing_detected=analysis.trailing_detected,
    )
    return {
        **_build_dashboard_image(capture, analysis),
        "components": {
            **components,
            "stars_detected": analysis.stars_detected,
            "background_level": analysis.background_level,
            "background_variation": standard_deviation,
            "trailing_detected": analysis.trailing_detected,
        },
    }


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

    recommended_settings = get_recommended_settings(
        captures=captures,
        analyses_by_capture=analyses_by_capture,
    )
    preview_capture = next(
        (
            capture
            for capture in captures
            if capture.polaris_id == recommended_settings.get("polaris_id")
        ),
        None,
    )

    return {
        "object": object_name,
        "common_name": get_target_common_name(object_name),
        "profile": get_target_profile(object_name),
        "preview_url": (
            f"/operator-preview/{recommended_settings['polaris_id']}"
            if recommended_settings.get("polaris_id")
            else None
        ),
        "preview_image": (
            _build_dashboard_image(
                preview_capture,
                analyses_by_capture.get(preview_capture.id),
            )
            if preview_capture is not None
            else None
        ),
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
        "scored_capture_count": len(quality_scores),
        "latest_capture": latest_capture.observation_utc,
        "recommended_settings": recommended_settings,
        "status": portfolio["status"],
        "progress_percent": portfolio["progress_percent"],
        "portfolio_level": portfolio["portfolio_level"],
        "current_hours": portfolio["current_hours"],
        "goal_hours": portfolio["goal_hours"],
        "goal_tier": portfolio["goal_tier"],
        "goal_source": portfolio["goal_source"],
        "goal_options": portfolio["goal_options"],
        "goal_factors": portfolio["goal_factors"],
        "integration_goal_note": portfolio["integration_goal_note"],
        "remaining_hours": portfolio["remaining_hours"],
        "readiness_score": portfolio["readiness_score"],
        "quality_captures": [
            _build_quality_capture(capture, analysis)
            for capture in captures[:QUALITY_CAPTURE_LIMIT]
            if (
                (analysis := analyses_by_capture.get(capture.id))
                is not None
                and analysis.quality_score is not None
            )
        ],
    }


def _build_recent_capture(
    capture: Capture,
    analyses_by_capture: Dict[int, CaptureAnalysis],
    sessions_by_id: Dict[int, ObservingSession],
) -> Dict:
    integration_seconds = get_capture_integration_seconds(capture)
    analysis = analyses_by_capture.get(capture.id)
    session = sessions_by_id.get(capture.session_id)

    return {
        "polaris_id": capture.polaris_id,
        "preview_url": (
            f"/operator-preview/{capture.polaris_id}"
            if capture.polaris_id
            else None
        ),
        "object": capture.object_name,
        "common_name": get_target_common_name(capture.object_name),
        "filename": capture.filename,
        "observation_utc": capture.observation_utc,
        "status": capture.status,
        "session_id": session.session_id if session is not None else None,
        "location": (
            session.location or None
            if session is not None
            else None
        ),
        "bortle_class": (
            session.bortle_class
            if session is not None
            else None
        ),
        "observatory": (
            session.observatory
            if session is not None and session.observatory
            else OBSERVATORY_NAME
        ),
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
        "quality_recommendation": build_quality_improvement_recommendation(
            stars_detected=analysis.stars_detected if analysis is not None else None,
            median_value=analysis.background_level if analysis is not None else None,
            standard_deviation=_analysis_standard_deviation(analysis),
            trailing_detected=analysis.trailing_detected if analysis is not None else None,
        ),
        "components": (
            _build_quality_capture(capture, analysis)["components"]
            if analysis is not None
            else None
        ),
    }


def _build_recent_session(
    session: ObservingSession,
    captures: List[Capture],
    analyses_by_capture: Dict[int, CaptureAnalysis],
) -> Dict:
    total_seconds = sum(
        get_capture_integration_seconds(capture)
        for capture in captures
    )

    targets = sorted(
        {
            capture.object_name
            for capture in captures
            if capture.object_name
        }
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
    subframe_counts = [
        capture.subframe_count
        for capture in captures
        if capture.subframe_count is not None
    ]
    started_at = _session_start(captures)

    return {
        "session_id": session.session_id,
        "date": session.date,
        "started_at": (
            started_at.isoformat()
            if started_at is not None
            else None
        ),
        "location": session.location or None,
        "observatory": session.observatory or OBSERVATORY_NAME,
        "bortle_class": session.bortle_class,
        "capture_count": len(captures),
        "total_integration_seconds": total_seconds,
        "total_integration_hours": round(total_seconds / 3600, 2),
        "targets": targets,
        "target_labels": [
            _target_label(object_name)
            for object_name in targets
        ],
        "target_common_names": [
            get_target_common_name(object_name)
            for object_name in targets
        ],
        "total_subframes": (
            sum(subframe_counts)
            if subframe_counts
            else None
        ),
        "sub_exposure_seconds": _single_value(
            captures,
            "sub_exposure_seconds",
        ),
        "gain": _single_value(captures, "gain"),
        "filter_name": _single_value(captures, "filter_name"),
        "average_quality": (
            round(sum(quality_scores) / len(quality_scores), 1)
            if quality_scores
            else None
        ),
        "images": [
            _build_dashboard_image(
                capture,
                analyses_by_capture.get(capture.id),
            )
            for capture in captures
            if capture.polaris_id
        ],
    }


def build_dashboard_response(
    db: Session,
    include_all_history: bool = False,
) -> Dict:
    captures = db.query(Capture).all()
    captures.sort(key=_capture_sort_key, reverse=True)
    sessions = db.query(ObservingSession).all()
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

    sessions.sort(
        key=lambda session: _session_sort_key(
            session,
            captures_by_session.get(session.id, []),
        ),
        reverse=True,
    )
    sessions_with_captures = [
        session
        for session in sessions
        if captures_by_session.get(session.id)
    ]

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

    sessions_by_id = {
        session.id: session
        for session in sessions
    }
    total_integration_seconds = sum(
        get_capture_integration_seconds(capture)
        for capture in captures
    )
    capture_location_counts = defaultdict(int)
    capture_location_bortle_classes = defaultdict(set)
    for capture in captures:
        session = sessions_by_id.get(capture.session_id)
        if session is not None and session.location:
            capture_location_counts[session.location] += 1
            if session.bortle_class is not None:
                capture_location_bortle_classes[session.location].add(
                    session.bortle_class
                )

    capture_locations = []
    for location, capture_count in capture_location_counts.items():
        coordinates = CAPTURE_LOCATION_COORDINATES.get(location)
        if coordinates is None:
            continue
        capture_locations.append(
            {
                "location": location,
                "city_label": coordinates["city_label"],
                "latitude": coordinates["latitude"],
                "longitude": coordinates["longitude"],
                "capture_count": capture_count,
                "bortle_class": (
                    next(iter(capture_location_bortle_classes[location]))
                    if len(capture_location_bortle_classes[location]) == 1
                    else None
                ),
            }
        )
    capture_locations.sort(
        key=lambda location: (-location["capture_count"], location["city_label"])
    )

    return {
        "api_version": settings.VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "captures": len(captures),
            "targets": len(captures_by_target),
            "sessions": len(sessions),
            "sessions_with_captures": len(sessions_with_captures),
            "analysis_records": analysis_records,
            "total_integration_seconds": total_integration_seconds,
            "total_integration_hours": round(
                total_integration_seconds / 3600,
                2,
            ),
        },
        "targets": targets,
        "capture_locations": capture_locations,
        "recent_captures": [
            _build_recent_capture(
                capture=capture,
                analyses_by_capture=analyses_by_capture,
                sessions_by_id=sessions_by_id,
            )
            for capture in captures[
                :None if include_all_history else RECENT_CAPTURE_LIMIT
            ]
        ],
        "recent_sessions": [
            _build_recent_session(
                session=session,
                captures=captures_by_session.get(session.id, []),
                analyses_by_capture=analyses_by_capture,
            )
            for session in sessions_with_captures[
                :None if include_all_history else RECENT_SESSION_LIMIT
            ]
        ],
    }
