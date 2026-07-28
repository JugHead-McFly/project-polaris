from datetime import datetime
from datetime import timezone
from typing import Dict
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import HostedObservatory
from app.models import RecommendationFeedback
from app.models import RecommendationRun


PLANNER_VERSION = "Planner V3"
LOCAL_DATE_TIME_FORMAT = "%Y-%m-%d %I:%M %p"


def _parse_local_time(
    value: Optional[str],
    timezone_name: str,
) -> Optional[datetime]:
    if not value:
        return None
    try:
        local_time = datetime.strptime(value, LOCAL_DATE_TIME_FORMAT)
    except (TypeError, ValueError):
        return None
    return local_time.replace(
        tzinfo=ZoneInfo(timezone_name)
    ).astimezone(timezone.utc)


def _parse_iso_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def create_recommendation_run(
    db: Session,
    *,
    user_id: UUID,
    observatory: HostedObservatory,
    payload: Dict,
) -> RecommendationRun:
    schedule = payload["schedule"]
    weather = payload["weather"]
    darkness = payload["darkness"]
    recommended_target = payload.get("recommended_target")
    schedule_blocks = schedule.get("blocks") or []
    planned_start = (
        schedule_blocks[0].get("start")
        if schedule_blocks
        else darkness.get("astronomical_darkness_start")
    )
    planned_for = _parse_local_time(
        planned_start,
        observatory.timezone_name,
    ) or datetime.now(timezone.utc)

    run = RecommendationRun(
        user_id=user_id,
        observatory_id=observatory.id,
        planned_for=planned_for,
        forecast_observed_at=_parse_iso_time(
            weather.get("observed_at")
        ),
        outcome=schedule["decision"],
        primary_target=(
            recommended_target.get("object")
            if recommended_target
            else None
        ),
        explanation={
            "message": payload["message"],
            "notes": schedule.get("notes") or [],
            "target_reason": (
                recommended_target.get("reason")
                if recommended_target
                else None
            ),
        },
        input_provenance={
            "weather_status": weather.get("status"),
            "weather_observed_at": weather.get("observed_at"),
            "moon_illumination_percent": payload["moon"].get(
                "illumination_percent"
            ),
            "coordinates_are_approximate": (
                observatory.coordinates_are_approximate
            ),
        },
        planner_version=PLANNER_VERSION,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def save_recommendation_feedback(
    db: Session,
    *,
    user_id: UUID,
    recommendation_run_id: UUID,
    useful: bool,
    reason: Optional[str] = None,
) -> Optional[RecommendationFeedback]:
    run = (
        db.query(RecommendationRun)
        .filter(
            RecommendationRun.id == recommendation_run_id,
            RecommendationRun.user_id == user_id,
        )
        .one_or_none()
    )
    if run is None:
        return None

    feedback = (
        db.query(RecommendationFeedback)
        .filter(
            RecommendationFeedback.recommendation_run_id
            == recommendation_run_id,
            RecommendationFeedback.user_id == user_id,
        )
        .order_by(RecommendationFeedback.created_at)
        .first()
    )
    if feedback is None:
        feedback = RecommendationFeedback(
            user_id=user_id,
            observatory_id=run.observatory_id,
            recommendation_run_id=run.id,
            useful=useful,
            reason=reason,
        )
        db.add(feedback)
    else:
        feedback.useful = useful
        feedback.reason = reason

    db.commit()
    db.refresh(feedback)
    return feedback
