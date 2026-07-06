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


@router.get("/{polaris_id}")
def get_capture(polaris_id: str):
    db = SessionLocal()

    try:
        capture = (
            db.query(Capture)
            .filter(Capture.polaris_id == polaris_id)
            .first()
        )

        if capture is None:
            return {"error": "Capture not found"}

        return {
            "id": capture.id,
            "polaris_id": capture.polaris_id,
            "object_name": capture.object_name,
            "filename": capture.filename,
            "asset_path": capture.asset_path,
            "status": capture.status,
            "observation_utc": capture.observation_utc,
            "gain": capture.gain,
            "ra": capture.ra,
            "dec": capture.dec,
            "telescope": capture.telescope,
            "firmware": capture.firmware,
            "created_at": capture.created_at,
            "updated_at": capture.updated_at,
        }

    finally:
        db.close()