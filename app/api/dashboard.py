from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings
from app.database.database import SessionLocal
from app.models import Capture
from app.models import ObservingSession
from app.services.portfolio_service import TARGET_PRIORITY
from app.services.portfolio_service import build_portfolio_target

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard():
    db = SessionLocal()

    try:
        captures = db.query(Capture).order_by(Capture.id).all()

        latest_session = (
            db.query(ObservingSession)
            .order_by(ObservingSession.id.desc())
            .first()
        )

        total_captures = len(captures)

        total_integration_seconds = sum(
            capture.exposure_seconds or 0
            for capture in captures
        )

        total_integration_hours = round(
            total_integration_seconds / 3600,
            2,
        )

        average_hours_per_capture = round(
            total_integration_hours / max(total_captures, 1),
            2,
        )

        integration_by_object_seconds = {}
        captures_by_object = {}

        for capture in captures:
            if not capture.object_name:
                continue

            captures_by_object[capture.object_name] = (
                captures_by_object.get(capture.object_name, 0) + 1
            )

            integration_by_object_seconds[capture.object_name] = (
                integration_by_object_seconds.get(capture.object_name, 0)
                + (capture.exposure_seconds or 0)
            )

        integration_by_object_hours = {
            object_name: round(seconds / 3600, 2)
            for object_name, seconds
            in integration_by_object_seconds.items()
        }

        portfolio_by_target = {
            target: build_portfolio_target(
                object_name=target,
                total_hours=integration_by_object_hours.get(target, 0),
            )
            for target in TARGET_PRIORITY
        }

        progress_by_object = {
            target: data["progress_percent"]
            for target, data in portfolio_by_target.items()
            if data["progress_percent"] > 0
        }

        portfolio_level_by_object = {
            target: data["portfolio_level"]
            for target, data in portfolio_by_target.items()
            if data["progress_percent"] > 0
        }

        portfolio_counts = {
            "Not Started": 0,
            "Bronze": 0,
            "Silver": 0,
            "Gold": 0,
            "Platinum": 0,
        }

        for target in TARGET_PRIORITY:
            level = portfolio_by_target[target]["portfolio_level"]
            portfolio_counts[level] += 1

        project_progress_percent = round(
            sum(
                portfolio_by_target[target]["progress_percent"]
                for target in TARGET_PRIORITY
            )
            / len(TARGET_PRIORITY),
            1,
        )

        completed_targets = sum(
            1
            for target in TARGET_PRIORITY
            if portfolio_by_target[target]["progress_percent"] >= 100
        )

        unfinished_targets = [
            target
            for target in TARGET_PRIORITY
            if portfolio_by_target[target]["progress_percent"] < 100
        ]

        recommended_target = (
            unfinished_targets[0]
            if unfinished_targets
            else None
        )

        backup_target = (
            unfinished_targets[1]
            if len(unfinished_targets) > 1
            else None
        )

        recommendation_reasons = {
            "M16": "Highest priority target not yet completed.",
            "M17": "Continue building integration time.",
            "M20": "Strong summer target still pending.",
            "M11": "Excellent cluster target.",
            "M22": "Bright globular cluster target.",
        }

        backup_reasons = {
            "M16": "Strong secondary target if the primary is unavailable.",
            "M17": "Continue building toward the 6-hour integration goal.",
            "M20": "Good summer alternative target.",
            "M11": "Bright cluster that handles moonlight well.",
            "M22": "Bright globular cluster and reliable backup.",
        }

        latest = captures[-1] if captures else None
        capture_age_days = None

        if latest and latest.observation_utc:
            observation_datetime = datetime.fromisoformat(
                latest.observation_utc.replace("Z", "+00:00")
            )

            capture_age_days = (
                datetime.utcnow()
                - observation_datetime.replace(tzinfo=None)
            ).days

        unique_objects = sorted(
            set(
                capture.object_name
                for capture in captures
                if capture.object_name
            )
        )

        database_metrics = {
            "captures": total_captures,
            "sessions": db.query(ObservingSession).count(),
            "objects": len(unique_objects),
        }

        recommended_data = (
            portfolio_by_target[recommended_target]
            if recommended_target
            else None
        )

        backup_data = (
            portfolio_by_target[backup_target]
            if backup_target
            else None
        )

        return {
            "api_version": settings.VERSION,
            "system": {
                "status": "Healthy",
                "database": "Connected",
                "last_updated": datetime.utcnow().isoformat(),
            },
            "metrics": database_metrics,
            "observatory": {
                "name": "Doug's Observatory",
                "location": (
                    latest_session.location
                    if latest_session
                    else None
                ),
            },
            "statistics": {
                "total_integration_seconds": total_integration_seconds,
                "total_integration_hours": total_integration_hours,
                "integration_by_object_hours": integration_by_object_hours,
                "average_hours_per_capture": average_hours_per_capture,
                "portfolio_level_by_object": portfolio_level_by_object,
                "captures_by_object": captures_by_object,
                "portfolio_counts": portfolio_counts,
                "progress_by_object": progress_by_object,
                "total_captures": total_captures,
                "objects_imaged": len(unique_objects),
                "object_list": unique_objects,
                "completed_targets": completed_targets,
                "unfinished_targets": len(unfinished_targets),
            },
            "latest_capture": {
                "polaris_id": latest.polaris_id if latest else None,
                "object": latest.object_name if latest else None,
                "filename": latest.filename if latest else None,
                "observation_utc": (
                    latest.observation_utc
                    if latest
                    else None
                ),
                "exposure_seconds": (
                    latest.exposure_seconds
                    if latest
                    else None
                ),
                "telescope": latest.telescope if latest else None,
                "firmware": latest.firmware if latest else None,
                "gain": latest.gain if latest else None,
                "ra": latest.ra if latest else None,
                "dec": latest.dec if latest else None,
                "capture_age_days": capture_age_days,
                "status": latest.status if latest else None,
            },
            "current_session": {
                "session_id": (
                    latest_session.session_id
                    if latest_session
                    else None
                ),
                "date": (
                    latest_session.date
                    if latest_session
                    else None
                ),
                "location": (
                    latest_session.location
                    if latest_session
                    else None
                ),
            },
            "current_project": {
                "name": "Summer Emission Nebulae",
                "progress_percent": project_progress_percent,
                "completed_targets": completed_targets,
                "total_targets": len(TARGET_PRIORITY),
                "unfinished_targets": unfinished_targets,
            },
            "recommended_target": {
                "object": recommended_target,
                "reason": recommendation_reasons.get(
                    recommended_target,
                    "All portfolio targets completed.",
                ),
                "progress_percent": (
                    recommended_data["progress_percent"]
                    if recommended_data
                    else None
                ),
                "portfolio_level": (
                    recommended_data["portfolio_level"]
                    if recommended_data
                    else None
                ),
                "remaining_hours": (
                    recommended_data["remaining_hours"]
                    if recommended_data
                    else None
                ),
                "current_hours": (
                    recommended_data["current_hours"]
                    if recommended_data
                    else None
                ),
                "goal_hours": (
                    recommended_data["goal_hours"]
                    if recommended_data
                    else None
                ),
            },
            "backup_target": {
                "object": backup_target,
                "reason": backup_reasons.get(
                    backup_target,
                    "No backup target available.",
                ),
                "progress_percent": (
                    backup_data["progress_percent"]
                    if backup_data
                    else None
                ),
                "portfolio_level": (
                    backup_data["portfolio_level"]
                    if backup_data
                    else None
                ),
                "remaining_hours": (
                    backup_data["remaining_hours"]
                    if backup_data
                    else None
                ),
                "current_hours": (
                    backup_data["current_hours"]
                    if backup_data
                    else None
                ),
                "goal_hours": (
                    backup_data["goal_hours"]
                    if backup_data
                    else None
                ),
            },
        }

    finally:
        db.close()
