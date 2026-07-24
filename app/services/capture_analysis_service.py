from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Capture
from app.models import CaptureAnalysis
from app.services.analysis_service import analyze_fits_file


def clamp_score(value: float) -> int:
    return int(max(0, min(100, round(value))))


QUALITY_SCORING_VERSION = "2.0"

QUALITY_COMPONENT_MAXIMUMS = {
    "sharpness_points": 30,
    "roundness_points": 25,
    "signal_points": 20,
    "uniformity_points": 15,
    "clipping_points": 10,
}

EQUIPMENT_QUALITY_PROFILES = {
    "generic": {
        "label": "Generic deep-sky starter",
        "fwhm_best": 1.5,
        "fwhm_worst": 5.0,
    },
    "dwarf mini": {
        "label": "DWARF mini starter",
        "fwhm_best": 1.8,
        "fwhm_worst": 2.5,
    },
}

UNSUPPORTED_DEEP_SKY_TARGETS = {
    "JUPITER",
    "MARS",
    "MERCURY",
    "MOON",
    "NEPTUNE",
    "SATURN",
    "SUN",
    "URANUS",
    "VENUS",
}


def _equipment_quality_profile(
    telescope: Optional[str],
) -> Dict[str, Any]:
    key = (telescope or "").strip().lower()
    return EQUIPMENT_QUALITY_PROFILES.get(
        key,
        EQUIPMENT_QUALITY_PROFILES["generic"],
    )


def _lower_is_better_points(
    value: Optional[float],
    best: float,
    worst: float,
    maximum: int,
) -> int:
    if value is None:
        return 0
    if value <= best:
        return maximum
    if value >= worst:
        return 0
    fraction = (worst - value) / (worst - best)
    return int(round(maximum * fraction))


def _higher_is_better_points(
    value: Optional[float],
    worst: float,
    best: float,
    maximum: int,
) -> int:
    if value is None:
        return 0
    if value >= best:
        return maximum
    if value <= worst:
        return 0
    fraction = (value - worst) / (best - worst)
    return int(round(maximum * fraction))


def _quality_confidence(
    object_name: Optional[str],
    star_sample_count: Optional[int],
    measurements_complete: bool,
) -> str:
    if (object_name or "").strip().upper() in UNSUPPORTED_DEEP_SKY_TARGETS:
        return "unsupported"
    if not measurements_complete:
        return "incomplete"
    sample_count = star_sample_count or 0
    if sample_count >= 50:
        return "high"
    if sample_count >= 25:
        return "medium"
    if sample_count >= 10:
        return "limited"
    return "insufficient"


def calculate_quality_components_v2(
    *,
    object_name: Optional[str],
    telescope: Optional[str],
    star_sample_count: Optional[int],
    median_fwhm: Optional[float],
    median_roundness: Optional[float],
    median_star_snr: Optional[float],
    background_gradient: Optional[float],
    clipped_pixel_fraction: Optional[float],
) -> Dict[str, Any]:
    """Return explainable v2 measurements, points, confidence, and total."""
    profile = _equipment_quality_profile(telescope)
    measurements_complete = all(
        value is not None
        for value in (
            median_fwhm,
            median_roundness,
            median_star_snr,
            background_gradient,
            clipped_pixel_fraction,
        )
    )
    confidence = _quality_confidence(
        object_name=object_name,
        star_sample_count=star_sample_count,
        measurements_complete=measurements_complete,
    )

    sharpness_points = _lower_is_better_points(
        median_fwhm,
        best=profile["fwhm_best"],
        worst=profile["fwhm_worst"],
        maximum=QUALITY_COMPONENT_MAXIMUMS["sharpness_points"],
    )
    roundness_points = _lower_is_better_points(
        median_roundness,
        best=0.08,
        worst=0.35,
        maximum=QUALITY_COMPONENT_MAXIMUMS["roundness_points"],
    )
    signal_points = _higher_is_better_points(
        median_star_snr,
        worst=5.0,
        best=50.0,
        maximum=QUALITY_COMPONENT_MAXIMUMS["signal_points"],
    )
    uniformity_points = _lower_is_better_points(
        background_gradient,
        best=0.05,
        worst=0.60,
        maximum=QUALITY_COMPONENT_MAXIMUMS["uniformity_points"],
    )
    clipping_points = _lower_is_better_points(
        clipped_pixel_fraction,
        best=0.0001,
        worst=0.01,
        maximum=QUALITY_COMPONENT_MAXIMUMS["clipping_points"],
    )

    quality_score = None
    if confidence in {"high", "medium"}:
        quality_score = clamp_score(
            sharpness_points
            + roundness_points
            + signal_points
            + uniformity_points
            + clipping_points
        )

    return {
        "scoring_version": QUALITY_SCORING_VERSION,
        "profile_label": profile["label"],
        "confidence": confidence,
        "star_sample_count": star_sample_count,
        "median_fwhm": median_fwhm,
        "sharpness_points": sharpness_points,
        "median_roundness": median_roundness,
        "roundness_points": roundness_points,
        "median_star_snr": median_star_snr,
        "signal_points": signal_points,
        "background_gradient": background_gradient,
        "uniformity_points": uniformity_points,
        "clipped_pixel_fraction": clipped_pixel_fraction,
        "clipping_points": clipping_points,
        "quality_score": quality_score,
    }


def calculate_quality_score_v2(**metrics) -> Optional[int]:
    return calculate_quality_components_v2(
        **metrics
    )["quality_score"]


def build_quality_improvement_recommendation_v2(
    components: Dict[str, Any],
) -> str:
    confidence = components["confidence"]
    if confidence == "unsupported":
        return (
            "This capture needs a planetary or lunar quality model; the "
            "deep-sky star model does not produce a reliable score."
        )
    if confidence in {"insufficient", "limited"}:
        return (
            "Too few usable stars were measured for a reliable deep-sky score. "
            "Review focus manually and collect another capture before comparing."
        )
    if confidence == "incomplete":
        return (
            "Quality analysis is incomplete. Reanalyze the original FITS file "
            "before using this capture for comparison."
        )

    opportunities = [
        (
            QUALITY_COMPONENT_MAXIMUMS["sharpness_points"]
            - components["sharpness_points"],
            5,
            "Sharpness is the largest opportunity. Refocus carefully and "
            "capture when atmospheric seeing is steadier.",
        ),
        (
            QUALITY_COMPONENT_MAXIMUMS["roundness_points"]
            - components["roundness_points"],
            4,
            "Star shape is the largest opportunity. Check tracking, alignment, "
            "and field-edge distortion before collecting more frames.",
        ),
        (
            QUALITY_COMPONENT_MAXIMUMS["signal_points"]
            - components["signal_points"],
            3,
            "Star signal is the largest opportunity. Improve focus and sky "
            "clarity, or collect more usable frames under steadier conditions.",
        ),
        (
            QUALITY_COMPONENT_MAXIMUMS["uniformity_points"]
            - components["uniformity_points"],
            2,
            "Background uniformity is the largest opportunity. Avoid thin "
            "clouds and gradients, and review flat-field calibration.",
        ),
        (
            QUALITY_COMPONENT_MAXIMUMS["clipping_points"]
            - components["clipping_points"],
            1,
            "Highlight clipping is the largest opportunity. Reduce exposure or "
            "gain enough to protect bright stars.",
        ),
    ]
    gap, _, recommendation = max(
        opportunities,
        key=lambda opportunity: (
            opportunity[0],
            opportunity[1],
        ),
    )
    return recommendation if gap > 0 else (
        "No single major technical issue was found. Continue capturing under "
        "similar conditions to build a cleaner final integration."
    )


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
    components = calculate_quality_components_v2(
        object_name=capture.object_name,
        telescope=capture.telescope,
        star_sample_count=metrics.get(
            "star_sample_count"
        ),
        median_fwhm=metrics.get(
            "median_fwhm"
        ),
        median_roundness=metrics.get(
            "median_roundness"
        ),
        median_star_snr=metrics.get(
            "median_star_snr"
        ),
        background_gradient=metrics.get(
            "background_gradient"
        ),
        clipped_pixel_fraction=metrics.get(
            "clipped_pixel_fraction"
        ),
    )

    if (
        analysis.scoring_version != QUALITY_SCORING_VERSION
        and analysis.legacy_quality_score is None
        and analysis.quality_score is not None
    ):
        analysis.legacy_quality_score = (
            analysis.quality_score
        )

    analysis.stars_detected = stars_detected
    analysis.median_fwhm = metrics.get(
        "median_fwhm"
    )
    analysis.eccentricity = metrics.get(
        "eccentricity"
    )
    analysis.median_roundness = metrics.get(
        "median_roundness"
    )
    analysis.median_sharpness = metrics.get(
        "median_sharpness"
    )
    analysis.background_level = median_value
    analysis.background_noise = metrics.get(
        "background_noise"
    )
    analysis.relative_background_noise = metrics.get(
        "relative_background_noise"
    )
    analysis.background_gradient = metrics.get(
        "background_gradient"
    )
    analysis.clipped_pixel_fraction = metrics.get(
        "clipped_pixel_fraction"
    )
    analysis.snr = metrics.get(
        "median_star_snr"
    )
    analysis.star_sample_count = metrics.get(
        "star_sample_count"
    )
    analysis.trailing_detected = None
    analysis.quality_score = components[
        "quality_score"
    ]
    analysis.scoring_version = (
        QUALITY_SCORING_VERSION
    )
    analysis.analysis_confidence = components[
        "confidence"
    ]
    analysis.recommendation = (
        build_quality_improvement_recommendation_v2(
            components
        )
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
        "scoring_version": (
            analysis.scoring_version
        ),
        "analysis_confidence": (
            analysis.analysis_confidence
        ),
        "recommendation": (
            analysis.recommendation
        ),
    }
