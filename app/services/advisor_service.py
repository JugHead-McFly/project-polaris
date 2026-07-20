import math
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.services.goal_engine_service import build_integration_goal
from app.services.portfolio_service import get_target_metadata
from app.services.target_service import get_target_summary


def calculate_confidence(
    capture_count: int,
    quality_score: Optional[int],
    recommendation_source: str,
) -> int:
    confidence = 25

    if recommendation_source == "best_capture":
        confidence += 30
    elif recommendation_source == "capture_history":
        confidence += 20

    confidence += min(
        capture_count * 5,
        25,
    )

    if quality_score is not None:
        confidence += min(
            int(quality_score * 0.2),
            20,
        )

    return min(
        confidence,
        100,
    )


def build_advisor_recommendation(
    object_name: str,
    remaining_hours: float,
    additional_subframes: Optional[int],
    sub_exposure_seconds: Optional[int],
    gain: Optional[float],
    filter_name: Optional[str],
) -> str:
    if remaining_hours <= 0:
        return (
            f"{object_name} has reached its current integration goal. "
            "Additional imaging is optional and should focus on improving "
            "quality, conditions, or processing."
        )

    if (
        additional_subframes is None
        or sub_exposure_seconds is None
    ):
        return (
            f"{object_name} needs approximately "
            f"{remaining_hours:.2f} more hours, but Polaris does not yet "
            "have enough successful capture history to recommend a "
            "specific subframe plan."
        )

    settings = (
        f"{additional_subframes} additional "
        f"{sub_exposure_seconds}-second subframes"
    )

    if gain is not None:
        settings += f" at gain {gain:g}"

    if filter_name:
        settings += (
            f" using the {filter_name} filter"
        )

    return (
        f"Continue imaging {object_name}. Capture approximately "
        f"{settings} to reach the current integration goal."
    )


def get_exposure_advice(
    db: Session,
    object_name: str,
) -> Dict:
    normalized_name = (
        object_name
        .strip()
        .upper()
    )

    summary = get_target_summary(
        db=db,
        target_name=normalized_name,
    )

    current_seconds = summary[
        "total_integration_seconds"
    ]

    current_hours = round(
        current_seconds / 3600,
        2,
    )

    integration_goal = build_integration_goal(normalized_name)
    goal_hours = integration_goal["hours"]

    goal_seconds = int(
        round(
            goal_hours * 3600
        )
    )

    remaining_seconds = max(
        goal_seconds - current_seconds,
        0,
    )

    remaining_hours = round(
        remaining_seconds / 3600,
        2,
    )

    recommended_settings = summary[
        "recommended_settings"
    ]

    recommendation_source = (
        recommended_settings.get("source")
        or "none"
    )

    source_capture_id = (
        recommended_settings.get(
            "polaris_id"
        )
    )

    sub_exposure_seconds = (
        recommended_settings.get(
            "exposure_seconds"
        )
    )

    gain = recommended_settings.get(
        "gain"
    )

    filter_name = recommended_settings.get(
        "filter_name"
    )

    if sub_exposure_seconds is None:
        metadata = get_target_metadata(
            normalized_name
        )

        sub_exposure_seconds = metadata.get(
            "exposure_seconds"
        )

        gain = metadata.get(
            "gain"
        )

        filter_name = metadata.get(
            "recommended_filter"
        )

        recommendation_source = (
            "catalog_fallback"
        )

        source_capture_id = None

    additional_subframes = None

    if (
        sub_exposure_seconds is not None
        and sub_exposure_seconds > 0
    ):
        additional_subframes = math.ceil(
            remaining_seconds
            / sub_exposure_seconds
        )

    best_quality = summary.get(
        "best_quality"
    )

    confidence = calculate_confidence(
        capture_count=summary["captures"],
        quality_score=best_quality,
        recommendation_source=(
            recommendation_source
        ),
    )

    status = (
        "Complete"
        if remaining_seconds == 0
        else "Continue Imaging"
    )

    recommendation = build_advisor_recommendation(
        object_name=normalized_name,
        remaining_hours=remaining_hours,
        additional_subframes=(
            additional_subframes
        ),
        sub_exposure_seconds=(
            sub_exposure_seconds
        ),
        gain=gain,
        filter_name=filter_name,
    )

    return {
        "object": normalized_name,
        "status": status,
        "current_integration_seconds": (
            current_seconds
        ),
        "current_integration_hours": (
            current_hours
        ),
        "goal_hours": goal_hours,
        "goal_tier": integration_goal["tier"],
        "goal_source": integration_goal["source"],
        "goal_options": integration_goal["options"],
        "goal_factors": integration_goal["factors"],
        "integration_goal_note": integration_goal["note"],
        "remaining_seconds": (
            remaining_seconds
        ),
        "remaining_hours": (
            remaining_hours
        ),
        "recommended_sub_exposure_seconds": (
            sub_exposure_seconds
        ),
        "recommended_gain": gain,
        "recommended_filter": filter_name,
        "additional_subframes_needed": (
            additional_subframes
        ),
        "recommendation_source": (
            recommendation_source
        ),
        "source_capture_id": (
            source_capture_id
        ),
        "confidence": confidence,
        "recommendation": recommendation,
    }
