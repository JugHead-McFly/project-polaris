from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database.database import get_tenant_db
from app.models import Capture
from app.models import CaptureAnalysis
from app.schemas import (
    CaptureAnalysisResponse,
    CaptureDetail,
    CaptureSummary,
)
from app.services.capture_analysis_service import (
    analyze_and_save_capture,
)

router = APIRouter(prefix="/captures", tags=["Captures"])


@router.get("", response_model=List[CaptureSummary])
def list_captures(db: Session = Depends(get_tenant_db)):
    return db.query(Capture).order_by(Capture.id).all()


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
    ),
    db: Session = Depends(get_tenant_db),
):
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


@router.get(
    "/{polaris_id}/analysis",
    response_model=CaptureAnalysisResponse,
    responses={
        404: {
            "description": "Capture or analysis not found",
        }
    },
)
def get_capture_analysis(
    polaris_id: str = Path(
        ...,
        title="Polaris Capture ID",
        description="Unique capture identifier, for example POL-2026-000001",
        examples=["POL-2026-000001"],
    ),
    db: Session = Depends(get_tenant_db),
):
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

    analysis = (
        db.query(CaptureAnalysis)
        .filter(CaptureAnalysis.capture_id == capture.id)
        .order_by(CaptureAnalysis.id.desc())
        .first()
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis exists for capture '{polaris_id}'.",
        )

    return analysis


@router.post(
    "/{polaris_id}/analyze",
    response_model=CaptureAnalysisResponse,
    responses={
        404: {
            "description": "Capture not found",
        }
    },
)
def analyze_capture(
    polaris_id: str = Path(
        ...,
        title="Polaris Capture ID",
        description="Unique capture identifier, for example POL-2026-000001",
        examples=["POL-2026-000001"],
    ),
    db: Session = Depends(get_tenant_db),
):
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

    analyze_and_save_capture(
        db=db,
        capture=capture,
    )
    return (
        db.query(CaptureAnalysis)
        .filter(
            CaptureAnalysis.capture_id
            == capture.id
        )
        .order_by(CaptureAnalysis.id.desc())
        .first()
    )
