from datetime import datetime
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Capture
from app.models import CaptureAnalysis
from app.services.analysis_service import analyze_fits_file


def clamp_score(value: float) -> int:
    return int(max(0, min(100, round(value))))


def calculate_quality_components(
    stars_detected: Optional[int],
    median_value: Optional[float],
    standard_deviation: Optional[float],
    trailing_detected: Optional[bool],
) -> Dict[str, int]:
    star_points = 0
    if stars_detected is not None:
        if stars_detected >= 5000:
            star_points = 20
        elif stars_detected >= 2500:
            star_points = 15
        elif stars_detected >= 1000:
            star_points = 10
        elif stars_detected >= 300:
            star_points = 5
        elif stars_detected < 100:
            star_points = -10

    variation_points = 0
    if standard_deviation is not None:
        if 150 <= standard_deviation <= 1200:
            variation_points = 15
        elif 50 <= standard_deviation < 150:
            variation_points = 5
        elif 1200 < standard_deviation <= 3000:
            variation_points = 5
        elif standard_deviation > 5000:
            variation_points = -10

    background_points = 0
    if median_value is not None:
        if 5000 <= median_value <= 40000:
            background_points = 10
        elif median_value < 1000:
            background_points = -5
        elif median_value > 60000:
            background_points = -10

    trailing_points = 0
    if trailing_detected is True:
        trailing_points = -25
    elif trailing_detected is False:
        trailing_points = 5

    return {
        "base_points": 50,
        "star_points": star_points,
        "background_points": background_points,
        "variation_points": variation_points,
        "trailing_points": trailing_points,
    }


def calculate_quality_score(
    stars_detected: Optional[int],
    median_value: Optional[float],
    standard_deviation: Optional[float],
    trailing_detected: Optional[bool],
) -> Optional[int]:
    if (
        stars_detected is None
        and median_value is None
        and standard_deviation is None
        and trailing_detected is None
    ):
        return None

    components = calculate_quality_components(
        stars_detected=stars_detected,
        median_value=median_value,
        standard_deviation=standard_deviation,
        trailing_detected=trailing_detected,
    )

    return clamp_score(sum(components.values()))


def build_quality_improvement_recommendation(
    stars_detected: Optional[int],
    median_value: Optional[float],
    standard_deviation: Optional[float],
    trailing_detected: Optional[bool],
) -> str:
    """Return the one capture-quality change most likely to help next."""
    if (
        stars_detected is None
        and median_value is None
        and standard_deviation is None
        and trailing_detected is None
    ):
        return "Quality analysis is not available for this capture yet."

    components = calculate_quality_components(
        stars_detected=stars_detected,
        median_value=median_value,
        standard_deviation=standard_deviation,
        trailing_detected=trailing_detected,
    )
    opportunities = [
        (
            5 - components["trailing_points"],
            4,
            "Improve mount tracking or guiding before collecting more frames; "
            "star trailing had the largest impact on this image.",
        )
        if trailing_detected is True
        else (0, 0, ""),
        (
            20 - components["star_points"],
            1,
            f"Star detection is the largest scoring gap: {stars_detected} "
            f"stars earned {components['star_points']} of 20 points. Check "
            "focus and sky clarity before collecting more frames.",
        )
        if components["star_points"] < 20
        else (0, 0, ""),
        (
            10 - components["background_points"],
            3,
            (
                "Increase exposure enough to lift the background out of the "
                "too-dark range without clipping bright stars."
                if median_value is not None and median_value < 1000
                else "Reduce sky glow or exposure intensity; the background "
                "was brighter than the useful scoring range."
                if median_value is not None and median_value > 60000
                else "Fine-tune exposure and background calibration to bring "
                "the background closer to the useful range."
            ),
        )
        if components["background_points"] < 10
        else (0, 0, ""),
        (
            15 - components["variation_points"],
            2,
            "Capture under clearer, more even conditions and review flat-field "
            "calibration; uneven background variation reduced this score.",
        )
        if components["variation_points"] < 15
        else (0, 0, ""),
    ]
    _, _, recommendation = max(
        opportunities,
        key=lambda opportunity: (opportunity[0], opportunity[1]),
    )
    return recommendation or (
        "No single major issue was found. Continue capturing under similar "
        "conditions to build a cleaner final integration."
    )


def build_recommendation(
    width: Optional[int],
    height: Optional[int],
    stars_detected: Optional[int],
    median_value: Optional[float],
    standard_deviation: Optional[float],
    quality_score: Optional[int],
) -> str:
    parts = ["Image statistics calculated"]

    if width is not None and height is not None:
        parts.append(f"{width}x{height}")

    if stars_detected is not None:
        parts.append(f"stars={stars_detected}")

    if median_value is not None:
        parts.append(f"median={median_value:.2f}")

    if standard_deviation is not None:
        parts.append(
            f"stddev={standard_deviation:.2f}"
        )

    if quality_score is not None:
        parts.append(f"quality={quality_score}/100")

    return ", ".join(parts)


def get_or_create_capture_analysis(
    db: Session,
    capture: Capture,
) -> Tuple[CaptureAnalysis, bool]:
    analysis = (
        db.query(CaptureAnalysis)
        .filter(
            CaptureAnalysis.capture_id == capture.id
        )
        .order_by(CaptureAnalysis.id.desc())
        .first()
    )

    if analysis is not None:
        return analysis, False

    analysis = CaptureAnalysis(
        capture_id=capture.id,
    )

    db.add(analysis)

    return analysis, True


def analyze_and_save_capture(
    db: Session,
    capture: Capture,
) -> Dict:
    metrics = analyze_fits_file(capture)

    analysis, analysis_created = (
        get_or_create_capture_analysis(
            db=db,
            capture=capture,
        )
    )

    stars_detected = metrics.get(
        "stars_detected"
    )
    median_value = metrics.get(
        "median_value"
    )
    standard_deviation = metrics.get(
        "standard_deviation"
    )
    trailing_detected = metrics.get(
        "trailing_detected"
    )

    quality_score = calculate_quality_score(
        stars_detected=stars_detected,
        median_value=median_value,
        standard_deviation=standard_deviation,
        trailing_detected=trailing_detected,
    )

    analysis.stars_detected = stars_detected
    analysis.median_fwhm = metrics.get(
        "median_fwhm"
    )
    analysis.eccentricity = metrics.get(
        "eccentricity"
    )
    analysis.background_level = median_value
    analysis.snr = metrics.get(
        "snr"
    )
    analysis.trailing_detected = (
        trailing_detected
    )
    analysis.quality_score = quality_score
    analysis.recommendation = build_recommendation(
        width=metrics.get("width"),
        height=metrics.get("height"),
        stars_detected=stars_detected,
        median_value=median_value,
        standard_deviation=standard_deviation,
        quality_score=quality_score,
    )
    analysis.created_at = datetime.utcnow()

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "status": "analyzed",
        "analysis_created": analysis_created,
        "analysis_id": analysis.id,
        "capture_database_id": capture.id,
        "polaris_id": capture.polaris_id,
        "object_name": capture.object_name,
        "asset_path": capture.asset_path,
        "stars_detected": analysis.stars_detected,
        "background_level": (
            analysis.background_level
        ),
        "quality_score": (
            analysis.quality_score
        ),
        "recommendation": (
            analysis.recommendation
        ),
    }
