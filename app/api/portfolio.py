from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture
from app.services.portfolio_service import INTEGRATION_GOALS_HOURS
from app.services.portfolio_service import TARGET_PRIORITY
from app.services.portfolio_service import build_portfolio_target

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("")
def portfolio():
    db = SessionLocal()

    try:
        goals = INTEGRATION_GOALS_HOURS
        results = []

        for object_name, goal_hours in goals.items():
            captures = (
                db.query(Capture)
                .filter(Capture.object_name == object_name)
                .all()
            )

            total_seconds = sum(
                c.exposure_seconds or 0
                for c in captures
            )
            total_hours = round(total_seconds / 3600, 2)

            target = build_portfolio_target(
                object_name=object_name,
                total_hours=total_hours,
            )

            target["capture_count"] = len(captures)
            results.append(target)

        priority_order = {
            object_name: index
            for index, object_name in enumerate(
                TARGET_PRIORITY,
                start=1,
            )
        }

        results.sort(
            key=lambda item: (
                -item["readiness_score"],
                priority_order.get(item["object"], 999),
            )
        )

        recommended_order = [
            item["object"]
            for item in results
        ]

        return {
            "recommended_order": recommended_order,
            "targets": results,
        }

    finally:
        db.close()