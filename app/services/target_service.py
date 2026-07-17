from collections import Counter
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Capture
from app.models import CaptureAnalysis
from app.services.portfolio_service import build_portfolio_target


def get_capture_integration_seconds(
    capture: Capture,
) -> int:
    if capture.total_integration_seconds is not None:
        return capture.total_integration_seconds

    if (
        capture.sub_exposure_seconds is not None
        and capture.subframe_count is not None
    ):
        return (
            capture.sub_exposure_seconds
            * capture.subframe_count
        )

    return capture.exposure_seconds or 0


def get_latest_analysis_by_capture(
    db: Session,
    capture_ids: list,
) -> Dict[int, CaptureAnalysis]:
    latest_by_capture = {}

    analyses = (
        db.query(CaptureAnalysis)
        .filter(
            CaptureAnalysis.capture_id.in_(
                capture_ids
            )
        )
        .order_by(
            CaptureAnalysis.capture_id,
            CaptureAnalysis.id.desc(),
        )
        .all()
    )

    for analysis in analyses:
        if analysis.capture_id not in latest_by_capture:
            latest_by_capture[
                analysis.capture_id
            ] = analysis

    return latest_by_capture


def get_best_capture(
    captures: list,
    analyses_by_capture: Dict[
        int,
        CaptureAnalysis,
    ],
) -> Optional[Capture]:
    scored_captures = []

    for capture in captures:
        analysis = analyses_by_capture.get(
            capture.id
        )

        if (
            analysis is not None
            and analysis.quality_score is not None
        ):
            scored_captures.append(
                (
                    analysis.quality_score,
                    capture.id,
                    capture,
                )
            )

    if not scored_captures:
        return None

    scored_captures.sort(
        reverse=True,
        key=lambda item: (
            item[0],
            item[1],
        ),
    )

    return scored_captures[0][2]


def get_most_common_settings(
    captures: list,
) -> Tuple[
    Optional[int],
    Optional[float],
    Optional[str],
]:
    settings = []

    for capture in captures:
        if capture.sub_exposure_seconds is None:
            continue

        settings.append(
            (
                capture.sub_exposure_seconds,
                capture.gain,
                capture.filter_name,
            )
        )

    if not settings:
        return None, None, None

    most_common, _ = Counter(
        settings
    ).most_common(1)[0]

    return most_common


def get_recommended_settings(
    captures: list,
    analyses_by_capture: Dict[
        int,
        CaptureAnalysis,
    ],
) -> Dict:
    best_capture = get_best_capture(
        captures=captures,
        analyses_by_capture=(
            analyses_by_capture
        ),
    )

    if (
        best_capture is not None
        and best_capture.sub_exposure_seconds
        is not None
    ):
        return {
            "source": "best_capture",
            "polaris_id": (
                best_capture.polaris_id
            ),
            "exposure_seconds": (
                best_capture
                .sub_exposure_seconds
            ),
            "gain": best_capture.gain,
            "filter_name": (
                best_capture.filter_name
            ),
        }

    (
        exposure_seconds,
        gain,
        filter_name,
    ) = get_most_common_settings(
        captures
    )

    if exposure_seconds is not None:
        return {
            "source": "capture_history",
            "polaris_id": None,
            "exposure_seconds": (
                exposure_seconds
            ),
            "gain": gain,
            "filter_name": filter_name,
        }

    return {
        "source": "none",
        "polaris_id": None,
        "exposure_seconds": None,
        "gain": None,
        "filter_name": None,
    }


def get_target_summary(
    db: Session,
    target_name: str,
) -> Dict:
    captures = (
        db.query(Capture)
        .filter(
            Capture.object_name == target_name
        )
        .order_by(Capture.id)
        .all()
    )

    if not captures:
        raise ValueError(
            f"Target '{target_name}' was not found."
        )

    capture_ids = [
        capture.id
        for capture in captures
    ]

    analyses_by_capture = (
        get_latest_analysis_by_capture(
            db=db,
            capture_ids=capture_ids,
        )
    )

    quality_scores = [
        analysis.quality_score
        for analysis
        in analyses_by_capture.values()
        if analysis.quality_score is not None
    ]

    total_integration_seconds = sum(
        get_capture_integration_seconds(
            capture
        )
        for capture in captures
    )

    latest_capture = max(
        captures,
        key=lambda capture: (
            capture.observation_utc
            or ""
        ),
    )

    recommended_settings = (
        get_recommended_settings(
            captures=captures,
            analyses_by_capture=(
                analyses_by_capture
            ),
        )
    )

    return {
        "target": target_name,
        "captures": len(captures),
        "sessions": len(
            {
                capture.session_id
                for capture in captures
                if capture.session_id
                is not None
            }
        ),
        "total_integration_seconds": (
            total_integration_seconds
        ),
        "best_quality": (
            max(quality_scores)
            if quality_scores
            else None
        ),
        "average_quality": (
            round(
                sum(quality_scores)
                / len(quality_scores),
                1,
            )
            if quality_scores
            else None
        ),
        "latest_capture": (
            latest_capture.observation_utc
        ),
        "recommended_settings": (
            recommended_settings
        ),
        "recommended_more_time": None,
        "completion_status": None,
    }


def build_target_response(
    db: Session,
    target_name: str,
) -> Dict:
    """Build the complete, API-ready summary for a captured target."""
    normalized_name = target_name.strip().upper()
    summary = get_target_summary(
        db=db,
        target_name=normalized_name,
    )
    captures = (
        db.query(Capture)
        .filter(Capture.object_name == normalized_name)
        .order_by(Capture.id)
        .all()
    )
    analyses_by_capture = get_latest_analysis_by_capture(
        db=db,
        capture_ids=[capture.id for capture in captures],
    )
    total_seconds = summary["total_integration_seconds"]
    total_hours = round(total_seconds / 3600, 2)
    portfolio = build_portfolio_target(
        object_name=normalized_name,
        total_hours=total_hours,
    )
    capture_results = []

    for capture in captures:
        capture_integration_seconds = get_capture_integration_seconds(
            capture
        )
        analysis = analyses_by_capture.get(capture.id)
        capture_results.append(
            {
                "polaris_id": capture.polaris_id,
                "filename": capture.filename,
                "observation_utc": capture.observation_utc,
                "status": capture.status,
                "sub_exposure_seconds": capture.sub_exposure_seconds,
                "subframe_count": capture.subframe_count,
                "total_integration_seconds": capture_integration_seconds,
                "total_integration_hours": round(
                    capture_integration_seconds / 3600,
                    2,
                ),
                "gain": capture.gain,
                "filter_name": capture.filter_name,
                "quality_score": (
                    analysis.quality_score
                    if analysis is not None
                    else None
                ),
            }
        )

    return {
        "object": normalized_name,
        "capture_count": summary["captures"],
        "session_count": summary["sessions"],
        "total_integration_seconds": total_seconds,
        "total_integration_hours": total_hours,
        "best_quality": summary["best_quality"],
        "average_quality": summary["average_quality"],
        "latest_capture": summary["latest_capture"],
        "recommended_settings": summary["recommended_settings"],
        "constellation": portfolio["constellation"],
        "target_type": portfolio["target_type"],
        "difficulty": portfolio["difficulty"],
        "recommended_filter": portfolio["recommended_filter"],
        "recommended_exposure": portfolio["recommended_exposure"],
        "season_score": portfolio["season_score"],
        "science_priority": portfolio["science_priority"],
        "readiness_score": portfolio["readiness_score"],
        "status": portfolio["status"],
        "best_window": portfolio["best_window"],
        "progress_percent": portfolio["progress_percent"],
        "portfolio_level": portfolio["portfolio_level"],
        "next_action": portfolio["next_action"],
        "current_hours": portfolio["current_hours"],
        "goal_hours": portfolio["goal_hours"],
        "remaining_hours": portfolio["remaining_hours"],
        "estimated_nights_remaining": portfolio[
            "estimated_nights_remaining"
        ],
        "observable": portfolio["observable"],
        "current_altitude": portfolio["current_altitude"],
        "transit_time": portfolio["transit_time"],
        "moon_warning": portfolio["moon_warning"],
        "recommended_start": portfolio["recommended_start"],
        "recommended_end": portfolio["recommended_end"],
        "moon_separation_degrees": None,
        "reason": None,
        "captures": capture_results,
    }
