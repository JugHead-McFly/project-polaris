from fastapi import APIRouter, HTTPException, Path

from app.database.database import SessionLocal
from app.models import Capture
from app.models import CaptureAnalysis
from app.schemas.target import TargetSummary
from app.services.portfolio_service import build_portfolio_target
from app.services.target_service import get_target_summary


router = APIRouter(
    prefix="/objects",
    tags=["Objects"],
)


@router.get(
    "/{object_name}",
    response_model=TargetSummary,
    responses={
        404: {
            "description": "Target not found",
        }
    },
)
def get_object_summary(
    object_name: str = Path(
        ...,
        title="Target name",
        description=(
            "Astronomical target designation, "
            "for example M17, M51, or NGC6633."
        ),
        examples=["M17"],
    )
):
    normalized_name = object_name.strip().upper()

    db = SessionLocal()

    try:
        try:
            summary = get_target_summary(
                db=db,
                target_name=normalized_name,
            )

        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Target '{normalized_name}' "
                    "was not found."
                ),
            )

        captures = (
            db.query(Capture)
            .filter(
                Capture.object_name == normalized_name
            )
            .order_by(Capture.id)
            .all()
        )

        total_seconds = summary[
            "total_integration_seconds"
        ]

        total_hours = round(
            total_seconds / 3600,
            2,
        )

        portfolio = build_portfolio_target(
            object_name=normalized_name,
            total_hours=total_hours,
        )

        capture_results = []

        for capture in captures:
            analysis = (
                db.query(CaptureAnalysis)
                .filter(
                    CaptureAnalysis.capture_id
                    == capture.id
                )
                .order_by(
                    CaptureAnalysis.id.desc()
                )
                .first()
            )

            capture_integration_seconds = (
                capture.total_integration_seconds
            )

            if capture_integration_seconds is None:
                if (
                    capture.sub_exposure_seconds is not None
                    and capture.subframe_count is not None
                ):
                    capture_integration_seconds = (
                        capture.sub_exposure_seconds
                        * capture.subframe_count
                    )
                else:
                    capture_integration_seconds = 0

            capture_results.append(
                {
                    "polaris_id": capture.polaris_id,
                    "filename": capture.filename,
                    "observation_utc": (
                        capture.observation_utc
                    ),
                    "status": capture.status,
                    "sub_exposure_seconds": (
                        capture.sub_exposure_seconds
                    ),
                    "subframe_count": (
                        capture.subframe_count
                    ),
                    "total_integration_seconds": (
                        capture_integration_seconds
                    ),
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
            "total_integration_seconds": (
                total_seconds
            ),
            "total_integration_hours": (
                total_hours
            ),
            "best_quality": (
                summary["best_quality"]
            ),
            "average_quality": (
                summary["average_quality"]
            ),
            "latest_capture": (
                summary["latest_capture"]
            ),
            "recommended_settings": (
                summary["recommended_settings"]
            ),
            "constellation": (
                portfolio["constellation"]
            ),
            "target_type": (
                portfolio["target_type"]
            ),
            "difficulty": (
                portfolio["difficulty"]
            ),
            "recommended_filter": (
                portfolio["recommended_filter"]
            ),
            "recommended_exposure": (
                portfolio["recommended_exposure"]
            ),
            "season_score": (
                portfolio["season_score"]
            ),
            "science_priority": (
                portfolio["science_priority"]
            ),
            "readiness_score": (
                portfolio["readiness_score"]
            ),
            "status": portfolio["status"],
            "best_window": (
                portfolio["best_window"]
            ),
            "progress_percent": (
                portfolio["progress_percent"]
            ),
            "portfolio_level": (
                portfolio["portfolio_level"]
            ),
            "next_action": (
                portfolio["next_action"]
            ),
            "current_hours": (
                portfolio["current_hours"]
            ),
            "goal_hours": (
                portfolio["goal_hours"]
            ),
            "remaining_hours": (
                portfolio["remaining_hours"]
            ),
            "estimated_nights_remaining": (
                portfolio[
                    "estimated_nights_remaining"
                ]
            ),
            "observable": (
                portfolio["observable"]
            ),
            "current_altitude": (
                portfolio["current_altitude"]
            ),
            "transit_time": (
                portfolio["transit_time"]
            ),
            "moon_warning": (
                portfolio["moon_warning"]
            ),
            "recommended_start": (
                portfolio["recommended_start"]
            ),
            "recommended_end": (
                portfolio["recommended_end"]
            ),
            "moon_separation_degrees": None,
            "reason": None,
            "captures": capture_results,
        }

    finally:
        db.close()