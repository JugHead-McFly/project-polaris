from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture
from app.services.portfolio_service import build_portfolio_target

router = APIRouter(prefix="/objects", tags=["Objects"])


@router.get("/{object_name}")
def get_object_summary(object_name: str):
    db = SessionLocal()

    try:
        captures = (
            db.query(Capture)
            .filter(Capture.object_name == object_name.upper())
            .order_by(Capture.id)
            .all()
        )

        total_seconds = sum(c.exposure_seconds or 0 for c in captures)
        total_hours = round(total_seconds / 3600, 2)

        portfolio = build_portfolio_target(
            object_name=object_name.upper(),
            total_hours=total_hours,

)
      
        return {
            "object_name": object_name.upper(),
            "capture_count": len(captures),
            "total_integration_seconds": total_seconds,
            "total_integration_hours": total_hours,
            "goal_hours": portfolio["goal_hours"],
            "progress_percent": portfolio["progress_percent"],
            "portfolio_level": portfolio["portfolio_level"],
            "remaining_hours": portfolio["remaining_hours"],
            "captures": [
                {
                    "polaris_id": c.polaris_id,
                    "filename": c.filename,
                    "observation_utc": c.observation_utc,
                    "status": c.status,
                }
                for c in captures
            ],
        }

    finally:
        db.close()