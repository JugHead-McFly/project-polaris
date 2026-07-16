from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Path

from app.database.database import SessionLocal
from app.models import Capture
from app.models import CaptureAnalysis
from app.schemas import (
    CaptureAnalysisResponse,
    CaptureDetail,
    CaptureSummary,
)
from app.services.analysis_service import analyze_fits_file

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
    finally:
        db.close()


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

        metrics = analyze_fits_file(capture)

        existing_analysis = (
            db.query(CaptureAnalysis)
            .filter(CaptureAnalysis.capture_id == capture.id)
            .order_by(CaptureAnalysis.id.desc())
            .first()
        )

        if existing_analysis:
            analysis = existing_analysis
        else:
            analysis = CaptureAnalysis(
                capture_id=capture.id,
            )

        analysis.stars_detected = metrics["stars_detected"]
        analysis.median_fwhm = None
        analysis.eccentricity = None
        analysis.background_level = metrics["median_value"]
        analysis.snr = None
        analysis.trailing_detected = None
        analysis.quality_score = None
        analysis.recommendation = (
            "Image statistics calculated: "
            f'{metrics["width"]}x{metrics["height"]}, '
            f'stars={metrics["stars_detected"]}, '
            f'median={metrics["median_value"]:.2f}, '
            f'stddev={metrics["standard_deviation"]:.2f}'
        )
        analysis.created_at = datetime.utcnow()

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return analysis
    finally:
        db.close()