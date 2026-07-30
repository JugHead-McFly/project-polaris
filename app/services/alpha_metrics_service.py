"""Privacy-safe, aggregate health metrics for the private alpha."""

from collections import Counter
from datetime import datetime
from typing import Any
from typing import Optional

from sqlalchemy.orm import Session

from app.models import HostedObservatory
from app.models import Profile
from app.models import RecommendationFeedback
from app.models import RecommendationRun


def _isoformat(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def build_alpha_metrics_report(db: Session) -> dict[str, Any]:
    """Return aggregate alpha metrics without personal observatory data.

    This intentionally excludes user IDs, names, email addresses, coordinates,
    target names, free-text feedback, and individual recommendation details.
    """
    profile_count = db.query(Profile).count()
    observatory_user_count = (
        db.query(HostedObservatory.user_id).distinct().count()
    )
    runs = db.query(
        RecommendationRun.user_id,
        RecommendationRun.planned_for,
        RecommendationRun.outcome,
        RecommendationRun.created_at,
    ).all()
    feedback_values = db.query(RecommendationFeedback.useful).all()

    planned_dates_by_user: dict[object, set[object]] = {}
    outcomes = Counter()
    created_times = []
    for user_id, planned_for, outcome, created_at in runs:
        planned_dates_by_user.setdefault(user_id, set()).add(
            planned_for.date()
        )
        outcomes[outcome] += 1
        created_times.append(created_at)

    useful_count = sum(1 for (useful,) in feedback_values if useful)
    not_useful_count = len(feedback_values) - useful_count
    feedback_count = len(feedback_values)
    returning_planner_count = sum(
        1
        for planned_dates in planned_dates_by_user.values()
        if len(planned_dates) >= 2
    )

    return {
        "privacy": {
            "contains_personal_data": False,
            "excluded": [
                "names",
                "email_addresses",
                "user_ids",
                "observatory_names",
                "coordinates",
                "target_names",
                "feedback_comments",
            ],
        },
        "accounts": {
            "profiles_created": profile_count,
            "with_observing_home": observatory_user_count,
            "with_saved_plan": len(planned_dates_by_user),
            "returning_for_two_or_more_nights": returning_planner_count,
        },
        "recommendations": {
            "saved": len(runs),
            "by_outcome": dict(sorted(outcomes.items())),
            "first_saved_at": _isoformat(min(created_times, default=None)),
            "last_saved_at": _isoformat(max(created_times, default=None)),
        },
        "feedback": {
            "responses": feedback_count,
            "useful": useful_count,
            "not_useful": not_useful_count,
            "response_rate_percent": round(
                feedback_count / len(runs) * 100, 1
            )
            if runs
            else None,
        },
    }
