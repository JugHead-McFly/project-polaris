import math
from typing import Dict, Optional

from app.data.targets import get_target_profile


KNOWN_FILTERS = {"astro": "Astro", "duo-band": "Duo-Band"}
SUPPORTED_EXPOSURES = (15, 30, 60)


def _normalized_filter(filter_name: Optional[str]) -> Optional[str]:
    if not filter_name:
        return None

    normalized = filter_name.strip().lower().replace("_", "-")
    if normalized in {"duoband", "duo band"}:
        normalized = "duo-band"
    return KNOWN_FILTERS.get(normalized, filter_name)


def _target_type(object_name: str) -> str:
    normalized_name = object_name.strip().upper()
    profile = get_target_profile(normalized_name) or {}
    if not profile:
        # Caldwell entries are stored as "C 20", while telescope metadata
        # commonly reports the same object as "C20".
        compact_prefix = normalized_name[:1]
        compact_number = normalized_name[1:]
        if compact_prefix in {"C", "M"} and compact_number.isdigit():
            profile = get_target_profile(
                f"{compact_prefix} {compact_number}"
            ) or {}
    return str(profile.get("object_type") or "Unknown").lower()


def _is_emission_target(target_type: str) -> bool:
    return "emission" in target_type or "planetary nebula" in target_type


def _is_broadband_target(target_type: str) -> bool:
    return any(
        label in target_type
        for label in ("galaxy", "cluster", "reflection")
    ) and not _is_emission_target(target_type)


def _moon_is_relevant(moon_warning: Optional[str]) -> bool:
    warning = (moon_warning or "").lower()
    return not (
        warning.startswith("none")
        or "below the horizon" in warning
        or warning.startswith("minimal")
    )


def _supported_exposure(value: Optional[int]) -> int:
    if value in SUPPORTED_EXPOSURES:
        return int(value)
    if value is not None and value > 0:
        # Preserve a user's successful historical setting even when it is outside
        # the current catalog choices (for example a successful 10-second run).
        return int(value)
    return 15


def recommend_imaging_settings(
    *,
    object_name: str,
    base_exposure_seconds: Optional[int],
    base_gain: Optional[float],
    base_filter: Optional[str],
    recommendation_source: str,
    weather: Dict,
    moon: Dict,
    moon_warning: Optional[str],
    moon_separation_degrees: Optional[float],
    bortle_class: Optional[int],
    equatorial_mode_enabled: Optional[bool] = None,
) -> Dict:
    """Return conservative, explainable settings for tonight's conditions.

    These rules choose settings only. Weather safety and the final
    Proceed/Caution/Do Not Image decision remain the planner's responsibility.
    """
    target_type = _target_type(object_name)
    emission_target = _is_emission_target(target_type)
    broadband_target = _is_broadband_target(target_type)
    source = recommendation_source or "none"
    historical_source = source in {"best_capture", "capture_history"}

    exposure_seconds = _supported_exposure(base_exposure_seconds)
    gain = float(base_gain) if base_gain is not None else 60.0
    filter_name = _normalized_filter(base_filter)
    reasons = []
    setup_guidance = []
    adjustments = []

    moon_illumination = moon.get("illumination_percent")
    moon_relevant = _moon_is_relevant(moon_warning)
    bright_moon = (
        moon_illumination is not None
        and moon_illumination >= 60
        and moon_relevant
    )
    close_moon = (
        moon_separation_degrees is not None
        and moon_separation_degrees < 40
        and moon_relevant
    )
    light_polluted = bortle_class is not None and bortle_class >= 6

    if broadband_target:
        if filter_name != "Astro":
            adjustments.append("filter")
        filter_name = "Astro"
        reasons.append(
            "Use the Astro filter for this galaxy or star cluster. It lets the "
            "camera collect the full range of starlight and natural color."
        )
    elif emission_target and (bright_moon or close_moon or light_polluted):
        if filter_name != "Duo-Band":
            adjustments.append("filter")
        filter_name = "Duo-Band"
        reason = (
            f"Use Duo-Band because {object_name} is a glowing-gas nebula. "
            "This filter keeps the red hydrogen and blue-green oxygen light "
            "that forms most of the nebula, while blocking much of the "
            "unwanted glow"
        )
        if bright_moon:
            reason += " from the Moon"
        elif light_polluted:
            reason += " from nearby lights"
        reason += "."
        reasons.append(reason)
    elif emission_target and filter_name == "Duo-Band":
        reasons.append(
            f"Use Duo-Band because {object_name} is a glowing-gas nebula. "
            "It helps the nebula stand out by keeping its red hydrogen and "
            "blue-green oxygen light while blocking much of the unwanted "
            "background glow."
        )
    elif emission_target and filter_name == "Astro":
        reasons.append(
            f"Use the Astro filter because it is the saved recipe for "
            f"{object_name}, and tonight's Moon and nearby lights do not "
            "require stronger filtering. Astro keeps a wider range of color."
        )
    elif filter_name:
        if filter_name == "Duo-Band":
            reasons.append(
                "Use Duo-Band to block much of the Moon and nearby light, "
                "helping the target stand out against a darker background."
            )
        else:
            reasons.append(
                "Use the Astro filter to collect a wide range of light and "
                "keep more natural star color."
            )

    wind_speed = weather.get(
        "planned_wind_speed_mph",
        weather.get("wind_speed_mph"),
    )
    if wind_speed is not None and wind_speed >= 12:
        if exposure_seconds > 15:
            exposure_seconds = 15
            adjustments.append("exposure")
        reasons.append(
            "Use 15-second exposures because strong wind may shake the "
            "telescope. A short exposure loses less time if one image is blurry."
        )
    elif (
        equatorial_mode_enabled is not True
        and exposure_seconds > 15
    ):
        previous_exposure_seconds = exposure_seconds
        exposure_seconds = 15
        adjustments.append("exposure")
        reasons.append(
            f"Use 15-second exposures instead of the saved "
            f"{previous_exposure_seconds}-second setting because equatorial "
            "tracking is not confirmed for tonight. DWARF's normal tracking "
            "mode is limited to 15 seconds."
        )
    elif wind_speed is not None and wind_speed >= 8:
        if exposure_seconds > 30:
            exposure_seconds = 30
            adjustments.append("exposure")
        reasons.append(
            "Keep each exposure at 30 seconds or less because the wind may "
            "make stars look soft or interrupt the telescope's tracking."
        )
    elif broadband_target and (bright_moon or light_polluted):
        if exposure_seconds > 15:
            exposure_seconds = 15
            adjustments.append("exposure")
        reasons.append(
            "Use 15-second exposures so Moon or city glow does not make the "
            "whole image too bright before the exposure finishes."
        )
    elif (
        emission_target
        and filter_name == "Duo-Band"
        and exposure_seconds == 15
        and (wind_speed is None or wind_speed < 8)
        and equatorial_mode_enabled is True
    ):
        exposure_seconds = 30
        adjustments.append("exposure")
        exposure_reason = (
            "Use 30-second exposures to gather more light in each image. "
            "Equatorial tracking is confirmed, tonight's wind is gentle, and "
            "Duo-Band keeps much of the unwanted background glow under control. "
        )
        if historical_source:
            exposure_reason += (
                "Your successful 15-second setting remains the safer fallback if "
                "tracking becomes unstable."
            )
        else:
            exposure_reason += (
                "Return to 15 seconds if tracking becomes unstable."
            )
        reasons.append(exposure_reason)
    elif (
        emission_target
        and filter_name == "Duo-Band"
        and not historical_source
        and exposure_seconds == 15
        and (wind_speed is None or wind_speed < 8)
    ):
        reasons.append(
            "Use 15-second exposures because Polaris has not been told that "
            "equatorial tracking is enabled. DWARF's normal tracking mode is "
            "limited to 15 seconds; 30 seconds or longer requires EQ mode. "
            "Polaris will split a long session into separate 999-frame runs "
            "instead of assuming a tracking mode that may not be set."
        )
    elif historical_source:
        reasons.append(
            f"Keep the exposure at {exposure_seconds} seconds because your "
            "previous captures of this target scored well with that setting, "
            "and tonight's conditions do not require a shorter exposure."
        )
    else:
        reasons.append(
            f"Start with {exposure_seconds}-second exposures. This is a safe "
            "beginner setting while Polaris learns what works best for your "
            "telescope and location."
        )

    # Gain is deliberately stable until Polaris has enough same-target evidence
    # to show that a change improves quality. High gain cannot recover signal lost
    # to cloud, Moon glow, or thermal noise.
    if gain < 40:
        gain = 60.0
        adjustments.append("gain")
        reasons.append(
            "Gain does not collect more light; it controls how strongly the "
            "camera turns the captured signal into pixel brightness. Higher "
            "gain makes faint detail show more strongly, but bright stars reach "
            "pure white sooner—losing detail—and noise becomes more visible. "
            "Lower gain preserves more detail in bright stars, but faint detail "
            "looks weaker in each frame. Set gain to 60 because very low DWARF gain "
            "can also create faint stripes in the image."
        )
    else:
        reasons.append(
            "Gain does not collect more light; it controls how strongly the "
            "camera turns the captured signal into pixel brightness. Raising "
            "gain makes faint detail show more strongly, but bright stars reach "
            "pure white sooner—losing detail—and noise becomes more visible. "
            "Lowering gain preserves more detail in bright stars, but faint "
            f"detail looks weaker in each frame. Keep gain at {gain:g} because it is already "
            "appropriate for this target. Changing gain cannot recover light "
            "blocked by clouds or remove Moon glow or heat noise."
        )

    temperature_f = weather.get("planned_temperature_f")
    if temperature_f is None:
        temperature_f = weather.get("temperature_f")
    if temperature_f is not None and temperature_f >= 95:
        setup_guidance.append(
            "Use dark frames matched to this exposure and gain at the session "
            "temperature; heat raises sensor noise."
        )

    if "exposure" in adjustments or "gain" in adjustments:
        setup_guidance.append(
            f"Confirm a matching {exposure_seconds}-second, gain {gain:g} dark "
            "calibration before starting."
        )

    cloud_cover = weather.get(
        "planned_cloud_cover_percent",
        weather.get("cloud_cover_percent"),
    )
    if cloud_cover is not None and cloud_cover >= 25:
        reasons.append(
            "Clouds affect whether you should image, but not these camera "
            "settings. A longer exposure cannot collect light that a cloud "
            "has blocked."
        )

    if historical_source and not adjustments:
        confidence = "Based on your capture history"
    elif historical_source:
        confidence = "Capture history adjusted for tonight"
    else:
        confidence = "Beginner-safe starting point"

    return {
        "sub_exposure_seconds": exposure_seconds,
        "gain": gain,
        "filter": filter_name or "Unknown",
        "confidence_label": confidence,
        "reasons": reasons,
        "setup_guidance": setup_guidance,
        "adjustments": sorted(set(adjustments)),
        "target_type": target_type.title(),
    }


def apply_tonight_settings(
    *,
    advisor: Dict,
    weather: Dict,
    moon: Dict,
    moon_warning: Optional[str],
    moon_separation_degrees: Optional[float],
    bortle_class: Optional[int],
    equatorial_mode_enabled: Optional[bool] = None,
) -> Dict:
    settings = recommend_imaging_settings(
        object_name=advisor["object"],
        base_exposure_seconds=advisor.get(
            "recommended_sub_exposure_seconds"
        ),
        base_gain=advisor.get("recommended_gain"),
        base_filter=advisor.get("recommended_filter"),
        recommendation_source=advisor.get("recommendation_source") or "none",
        weather=weather,
        moon=moon,
        moon_warning=moon_warning,
        moon_separation_degrees=moon_separation_degrees,
        bortle_class=bortle_class,
        equatorial_mode_enabled=equatorial_mode_enabled,
    )

    updated = dict(advisor)
    updated["recommended_sub_exposure_seconds"] = settings[
        "sub_exposure_seconds"
    ]
    updated["recommended_gain"] = settings["gain"]
    updated["recommended_filter"] = settings["filter"]
    updated["settings_confidence"] = settings["confidence_label"]
    updated["settings_reasons"] = settings["reasons"]
    updated["settings_setup_guidance"] = settings["setup_guidance"]
    updated["settings_adjustments"] = settings["adjustments"]
    updated["target_type"] = settings["target_type"]

    remaining_seconds = max(int(updated.get("remaining_seconds") or 0), 0)
    exposure_seconds = settings["sub_exposure_seconds"]
    updated["additional_subframes_needed"] = (
        math.ceil(remaining_seconds / exposure_seconds)
        if exposure_seconds > 0
        else None
    )
    return updated
