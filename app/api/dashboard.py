from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture
from app.models import ObservingSession
from datetime import datetime
from app.services.portfolio_service import INTEGRATION_GOALS_HOURS
from app.services.portfolio_service import TARGET_PRIORITY
from app.services.portfolio_service import get_portfolio_level

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard():
    db = SessionLocal()

    try:
        captures = db.query(Capture).all()

        latest_session = (
            db.query(ObservingSession)
            .order_by(ObservingSession.id.desc())
            .first()
        )

        total_captures = len(captures)
        total_integration_seconds = sum(
        c.exposure_seconds or 0
        for c in captures
        )
        total_integration_hours = round(
            total_integration_seconds / 3600,
            2,
        )
        imaging_efficiency = round(
            (
                total_integration_hours
                / max(total_captures, 1)
            ),
            2,
        )
        integration_by_object = {}
        captures_by_object = {}

        for capture in captures:
            captures_by_object[capture.object_name] = (
            captures_by_object.get(capture.object_name, 0) + 1
        )
            if not capture.object_name:
                continue

            integration_by_object[capture.object_name] = (
                integration_by_object.get(capture.object_name, 0)
                + (capture.exposure_seconds or 0)
            )

        integration_by_object_hours = {
            object_name: round(seconds / 3600, 2)
            for object_name, seconds in integration_by_object.items()
        }
        integration_goals_hours = INTEGRATION_GOALS_HOURS

        remaining_hours_by_object = {}

        for object_name, goal in integration_goals_hours.items():
            current = integration_by_object_hours.get(object_name, 0)
            remaining_hours_by_object[object_name] = round(
                max(goal - current, 0),
                2,
            )


        progress_by_object = {
            object_name: min(
                round(
                    (
                        hours
                        / integration_goals_hours.get(object_name, 4.0)
                    )
                    * 100,
                    1,
                ),
                100.0,
            )
            for object_name, hours in integration_by_object_hours.items()
        }

        portfolio_level_by_object = {}
       
        for object_name, progress in progress_by_object.items():
            level = get_portfolio_level(progress)
            portfolio_level_by_object[object_name] = level

        unique_objects = sorted(
            set(c.object_name for c in captures if c.object_name)
        )
        target_priority = TARGET_PRIORITY

        portfolio_counts = {
            "Not Started": 0,
            "Bronze": 0,
            "Silver": 0,
            "Gold": 0,
            "Platinum": 0,
        }

        for target in target_priority:
            level = portfolio_level_by_object.get(target, "Not Started")
            portfolio_counts[level] += 1


        recommended_target = next(
            (
                target
                for target in target_priority
                if progress_by_object.get(target, 0) < 100
            ),
            "Mission Complete",
        )

        project_progress_percent = round(
            sum(
                progress_by_object.get(target, 0)
                for target in target_priority
            )
            / len(target_priority),
            1,
        )

        completed_targets = sum(
            1
            for target in target_priority
            if progress_by_object.get(target, 0) >= 100
        )

        total_targets = len(target_priority)
        unfinished_targets = [
            target
            for target in target_priority
            if progress_by_object.get(target, 0) < 100
]

        backup_target = next(
            (
                target
                for target in target_priority
                if target != recommended_target
                and progress_by_object.get(target, 0) < 100
            ),
            None,
        )
        backup_reason = {
            "M16": "Strong secondary target if the primary is unavailable.",
            "M17": "Continue building toward the 6-hour integration goal.",
            "M20": "Good summer alternative target.",
            "M11": "Bright cluster that handles moonlight well.",
            "M22": "Bright globular cluster and reliable backup.",
        }.get(
            backup_target,
            "No backup target available.",
        )

        recommendation_reason = {
            "M16": "Highest priority target not yet completed.",
            "M17": "Continue building integration time.",
            "M20": "Strong summer target still pending.",
            "M11": "Excellent backup target.",
            "M22": "Low-priority backup target.",
        }.get(
            recommended_target,
            "All portfolio targets completed.",
        )


        latest = captures[-1] if captures else None
        capture_age_days = None

        if latest and latest.observation_utc:
            observation_datetime = datetime.fromisoformat(
                latest.observation_utc.replace("Z", "+00:00")
            )

            capture_age_days = (
                datetime.utcnow() - observation_datetime.replace(tzinfo=None)
            ).days
        total_sessions = db.query(ObservingSession).count()

        raw_captures = db.query(Capture).count()
        raw_sessions = db.query(ObservingSession).count()

        database_metrics = {
            "captures": raw_captures,
            "sessions": raw_sessions,
            "objects": len(unique_objects),
        }

        return {
            "api_version": "0.6",
            "system": {
                "status": "Healthy",
                "database": "Connected",
                "last_updated": datetime.utcnow().isoformat(),
            },
            "metrics": database_metrics,
            "observatory": {
                "name": "Doug's Observatory",
                "location": latest_session.location if latest_session else None,
            },
            "statistics": {
                "total_integration_seconds": total_integration_seconds,
                "total_integration_hours": total_integration_hours,
                "integration_by_object_hours": integration_by_object_hours,
                "average_hours_per_capture": imaging_efficiency,
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
                "observation_utc": latest.observation_utc if latest else None,
                "exposure_seconds": latest.exposure_seconds if latest else None,
                "telescope": latest.telescope if latest else None,
                "firmware": latest.firmware if latest else None,
                "gain": latest.gain if latest else None,
                "ra": latest.ra if latest else None,
                "dec": latest.dec if latest else None,
                "capture_age_days": capture_age_days,
                "status": latest.status if latest else None,
            },
            "current_session": {
                "session_id": latest_session.session_id if latest_session else None,
                "date": latest_session.date if latest_session else None,
                "location": latest_session.location if latest_session else None,
            },
            "current_project": {
                "name": "Summer Emission Nebulae",
                "progress_percent": project_progress_percent,
                "completed_targets": completed_targets,
                "total_targets": total_targets,
                "unfinished_targets": unfinished_targets,
            },
            "recommended_target": {
                "object": recommended_target,
                "reason": recommendation_reason,
                "progress_percent": progress_by_object.get(recommended_target, 0),
                "portfolio_level": portfolio_level_by_object.get(
                    recommended_target,
                    "Not Started",
                ),
                "remaining_hours": remaining_hours_by_object.get(
                    recommended_target,
                    0,
                ),
                "current_hours": integration_by_object_hours.get(
                    recommended_target,
                    0,
                ),
                "goal_hours": integration_goals_hours.get(
                    recommended_target,
                    0,
                ),
            },
            "backup_target": {
                "object": backup_target,
                "reason": backup_reason,
                "progress_percent": progress_by_object.get(backup_target, 0)
                if backup_target
                else None,
                "portfolio_level": portfolio_level_by_object.get(
                    backup_target,
                    "Not Started",
                )
                if backup_target
                else None,
                "remaining_hours": remaining_hours_by_object.get(
                    backup_target,
                    0,
                )
                if backup_target
                else None,
                "current_hours": integration_by_object_hours.get(
                    backup_target,
                    0,
                )
                if backup_target
                else None,
                "goal_hours": integration_goals_hours.get(
                    backup_target,
                    0,
                )
                if backup_target
                else None,
            },
        }

    finally:
        db.close()