from fastapi import APIRouter
from app.database.database import SessionLocal
from app.models import Capture

router = APIRouter(prefix="/captures", tags=["Captures"])


@router.get("")
def list_captures():
    db = SessionLocal()

    try:
        captures = db.query(Capture).order_by(Capture.id).all()

        return [
            {
                "polaris_id": c.polaris_id,
                "object_name": c.object_name,
                "filename": c.filename,
                "status": c.status,
                "observation_utc": c.observation_utc,
            }
            for c in captures
        ]

    finally:
        db.close()