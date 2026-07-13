from typing import List

from fastapi import APIRouter, HTTPException, Path

from app.database.database import SessionLocal
from app.models import Capture
from app.schemas import CaptureDetail
from app.schemas import CaptureSummary

router = APIRouter(prefix="/captures", tags=["Captures"])


@router.get("", response_model=List[CaptureSummary])
def list_captures():
    db = SessionLocal()

    try:
        return db.query(Capture).order_by(Capture.id).all()

    finally:
        db.close()


@router.get(
    "/{polaris_id}",
    response_model=CaptureDetail,
    responses={
        404: {
            "description": "Capture not found",
        }
    },
)
def get_capture(
    polaris_id: str = Path(
        ...,
        title="Polaris Capture ID",
        description="Unique capture identifier, for example POL-2026-000001",
        examples=["POL-2026-000001"],
    )
):
    db = SessionLocal()

    try:
        capture = (
            db.query(Capture)
            .filter(Capture.polaris_id == polaris_id)
            .first()
        )

        if capture is None:
            raise HTTPException(
                status_code=404,
                detail=f"Capture '{polaris_id}' was not found.",
            )

        return capture

    finally:
        db.close()