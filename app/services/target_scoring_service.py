from dataclasses import dataclass
from typing import Iterable, List, Optional

from app.data.rig_profiles import RigProfile


@dataclass(frozen=True)
class TargetScoringInputs:
    """Inputs for an experimental target-opportunity score.

    This does not replace the live planner score. It is a staging model for the
    more technical scoring direction captured from alpha research: sky
    brightness, Moon, target geometry, equipment fit, and exposure confidence.
    """

    maximum_altitude_degrees: Optional[float]
    usable_dark_minutes: int
    moon_illumination_percent: Optional[float]
    moon_separation_degrees: Optional[float]
    bortle_class: Optional[int]
    target_fits_field_of_view: Optional[bool] = None
    field_of_view_fit_label: Optional[str] = None
    exposure_confidence: Optional[float] = None


@dataclass(frozen=True)
class TargetScoringComponent:
    label: str
    points: int
    reason: str


@dataclass(frozen=True)
class TargetScoringResult:
    score: int
    quality: str
    components: List[TargetScoringComponent]


@dataclass(frozen=True)
class RigTargetScoringResult:
    rig_key: str
    rig_label: str
    score: int
    quality: str
    field_of_view_label: str
    result: TargetScoringResult


def _clamp_score(score: int) -> int:
    return max(0, min(100, score))


def _altitude_component(altitude: Optional[float]) -> TargetScoringComponent:
    if altitude is None:
        return TargetScoringComponent("Altitude", -20, "Target altitude is unknown.")
    if altitude >= 70:
        return TargetScoringComponent("Altitude", 25, "Target reaches a very high altitude.")
    if altitude >= 55:
        return TargetScoringComponent("Altitude", 20, "Target reaches a strong altitude.")
    if altitude >= 40:
        return TargetScoringComponent("Altitude", 12, "Target reaches a usable altitude.")
    if altitude >= 25:
        return TargetScoringComponent("Altitude", 4, "Target stays fairly low.")
    return TargetScoringComponent("Altitude", -25, "Target stays too close to the horizon.")


def _window_component(usable_minutes: int) -> TargetScoringComponent:
    if usable_minutes >= 240:
        return TargetScoringComponent("Usable window", 20, "Four or more dark hours are usable.")
    if usable_minutes >= 180:
        return TargetScoringComponent("Usable window", 16, "At least three dark hours are usable.")
    if usable_minutes >= 120:
        return TargetScoringComponent("Usable window", 10, "At least two dark hours are usable.")
    if usable_minutes >= 60:
        return TargetScoringComponent("Usable window", 3, "The usable window is short.")
    return TargetScoringComponent("Usable window", -20, "The usable window is too short.")


def _moon_component(
    illumination: Optional[float],
    separation: Optional[float],
) -> TargetScoringComponent:
    if illumination is None or separation is None:
        return TargetScoringComponent("Moon", -5, "Moon impact is incomplete.")
    if illumination < 35 or separation >= 90:
        return TargetScoringComponent("Moon", 15, "Moon impact is low.")
    if illumination < 65 and separation >= 60:
        return TargetScoringComponent("Moon", 8, "Moon impact is manageable.")
    if separation < 35:
        return TargetScoringComponent("Moon", -20, "The Moon is close to the target.")
    if illumination >= 80:
        return TargetScoringComponent("Moon", -12, "The Moon is very bright.")
    return TargetScoringComponent("Moon", -4, "Moonlight may reduce contrast.")


def _sky_brightness_component(bortle_class: Optional[int]) -> TargetScoringComponent:
    if bortle_class is None:
        return TargetScoringComponent("Sky brightness", 0, "Bortle class is not recorded.")
    if bortle_class <= 3:
        return TargetScoringComponent("Sky brightness", 15, "The site is a dark-sky location.")
    if bortle_class <= 5:
        return TargetScoringComponent("Sky brightness", 8, "The site has moderate sky brightness.")
    if bortle_class <= 7:
        return TargetScoringComponent("Sky brightness", -6, "The site is light polluted.")
    return TargetScoringComponent("Sky brightness", -15, "The site is very light polluted.")


def _field_of_view_component(
    fits: Optional[bool],
    fit_label: Optional[str],
) -> TargetScoringComponent:
    if fits is None:
        return TargetScoringComponent("Field of view", 0, "Field-of-view fit is not checked.")
    normalized_label = fit_label.strip().lower() if fit_label else ""
    if normalized_label == "very small":
        return TargetScoringComponent(
            "Field of view",
            2,
            "The target fits, but it will appear small in this rig.",
        )
    if normalized_label == "tight fit":
        return TargetScoringComponent(
            "Field of view",
            6,
            "The target fits, but framing tolerance is narrow.",
        )
    if normalized_label == "comfortable fit":
        return TargetScoringComponent("Field of view", 10, "The target fits the saved framing.")
    if fits:
        return TargetScoringComponent("Field of view", 8, "The target fits the saved framing.")
    return TargetScoringComponent("Field of view", -30, "The target does not fit the saved framing.")


def _exposure_confidence_component(confidence: Optional[float]) -> TargetScoringComponent:
    if confidence is None:
        return TargetScoringComponent("Exposure confidence", 0, "No exposure-confidence signal is available.")
    normalized = max(0.0, min(1.0, confidence))
    if normalized >= 0.85:
        return TargetScoringComponent("Exposure confidence", 15, "Exposure settings are strongly supported.")
    if normalized >= 0.6:
        return TargetScoringComponent("Exposure confidence", 8, "Exposure settings have moderate support.")
    if normalized >= 0.35:
        return TargetScoringComponent("Exposure confidence", 0, "Exposure settings are plausible but weakly supported.")
    return TargetScoringComponent("Exposure confidence", -10, "Exposure settings need validation.")


def _quality_label(score: int) -> str:
    if score >= 85:
        return "Excellent opportunity"
    if score >= 70:
        return "Strong opportunity"
    if score >= 55:
        return "Usable opportunity"
    if score >= 40:
        return "Marginal opportunity"
    return "Poor opportunity"


def score_target_opportunity(inputs: TargetScoringInputs) -> TargetScoringResult:
    """Score a target opportunity from 0-100 without changing live planning.

    The score starts at 50 so neutral or unknown inputs do not automatically
    fail a target. Strong geometry, dark sky, low Moon impact, FoV fit, and
    proven exposure settings move it up. Short windows, poor altitude, close
    bright Moon, heavy light pollution, poor FoV fit, or unvalidated exposure
    settings move it down.
    """

    components = [
        _altitude_component(inputs.maximum_altitude_degrees),
        _window_component(inputs.usable_dark_minutes),
        _moon_component(
            inputs.moon_illumination_percent,
            inputs.moon_separation_degrees,
        ),
        _sky_brightness_component(inputs.bortle_class),
        _field_of_view_component(
            inputs.target_fits_field_of_view,
            inputs.field_of_view_fit_label,
        ),
        _exposure_confidence_component(inputs.exposure_confidence),
    ]
    score = _clamp_score(50 + sum(component.points for component in components))
    return TargetScoringResult(
        score=score,
        quality=_quality_label(score),
        components=components,
    )


def score_target_opportunity_for_rig(
    *,
    rig: RigProfile,
    target_width_degrees: Optional[float],
    target_height_degrees: Optional[float],
    maximum_altitude_degrees: Optional[float],
    usable_dark_minutes: int,
    moon_illumination_percent: Optional[float],
    moon_separation_degrees: Optional[float],
    bortle_class: Optional[int],
    exposure_confidence: Optional[float] = None,
) -> TargetScoringResult:
    """Score a target opportunity using a saved rig profile's field of view."""

    fit = rig.assess_target_fit(target_width_degrees, target_height_degrees)
    return score_target_opportunity(
        TargetScoringInputs(
            maximum_altitude_degrees=maximum_altitude_degrees,
            usable_dark_minutes=usable_dark_minutes,
            moon_illumination_percent=moon_illumination_percent,
            moon_separation_degrees=moon_separation_degrees,
            bortle_class=bortle_class,
            target_fits_field_of_view=fit.fits,
            field_of_view_fit_label=fit.label,
            exposure_confidence=exposure_confidence,
        )
    )


def compare_target_opportunity_by_rig(
    *,
    rigs: Iterable[RigProfile],
    target_width_degrees: Optional[float],
    target_height_degrees: Optional[float],
    maximum_altitude_degrees: Optional[float],
    usable_dark_minutes: int,
    moon_illumination_percent: Optional[float],
    moon_separation_degrees: Optional[float],
    bortle_class: Optional[int],
    exposure_confidence: Optional[float] = None,
) -> List[RigTargetScoringResult]:
    """Rank the same target opportunity across multiple rig profiles."""

    scored: List[RigTargetScoringResult] = []
    for rig in rigs:
        fit = rig.assess_target_fit(target_width_degrees, target_height_degrees)
        result = score_target_opportunity(
            TargetScoringInputs(
                maximum_altitude_degrees=maximum_altitude_degrees,
                usable_dark_minutes=usable_dark_minutes,
                moon_illumination_percent=moon_illumination_percent,
                moon_separation_degrees=moon_separation_degrees,
                bortle_class=bortle_class,
                target_fits_field_of_view=fit.fits,
                field_of_view_fit_label=fit.label,
                exposure_confidence=exposure_confidence,
            )
        )
        scored.append(
            RigTargetScoringResult(
                rig_key=rig.key,
                rig_label=f"{rig.manufacturer} {rig.model}",
                score=result.score,
                quality=result.quality,
                field_of_view_label=fit.label,
                result=result,
            )
        )

    return sorted(
        scored,
        key=lambda entry: (
            entry.score,
            entry.field_of_view_label == "Comfortable fit",
            entry.field_of_view_label == "Tight fit",
        ),
        reverse=True,
    )
