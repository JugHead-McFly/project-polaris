from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard():
    db = SessionLocal()

    try:
        captures = db.query(Capture).all()

        total_captures = len(captures)

        unique_objects = sorted(
            set(c.object_name for c in captures if c.object_name)
        )

        latest = captures[-1] if captures else None

        return {
            "observatory": {
                "name": "Doug's Observatory",
                "location": "Huntsville, AL",
            },
            "statistics": {
                "total_captures": total_captures,
                "objects_imaged": len(unique_objects),
                "object_list": unique_objects,
            },
            "latest_capture": {
                "polaris_id": latest.polaris_id if latest else None,
                "object": latest.object_name if latest else None,
                "status": latest.status if latest else None,
            },
            "current_project": "Summer Emission Nebulae",
            "recommended_target": "M16",
        }

    finally:
        db.close()