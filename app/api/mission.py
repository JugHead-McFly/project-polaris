from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture

router = APIRouter(prefix="/mission", tags=["Mission"])


@router.get("/summary")
def mission_summary():
    db = SessionLocal()

    try:
        captures = db.query(Capture).order_by(Capture.id).all()

        total_captures = len(captures)
        objects = sorted(set(c.object_name for c in captures if c.object_name))

        return {
            "project": "Project Polaris",
            "summary": {
                "total_captures": total_captures,
                "unique_objects": len(objects),
                "objects_captured": objects,
            },
            "current_focus": {
                "project": "Summer Emission Nebulae",
                "highest_priority_remaining": [
                    "M16",
                    "M20",
                    "M11",
                    "M22"
                ],
                "recommended_next_target": "M16",
                "reason": "M17 is captured; M16 is the strongest remaining summer emission nebula target."
            }
        }

    finally:
        db.close()