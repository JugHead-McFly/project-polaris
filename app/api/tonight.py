from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.database.database import get_tenant_db
from app.schemas.tonight import TonightResponse
from app.data.rig_profiles import get_rig_profile
from app.data.targets import get_target_angular_size
from app.services.conditions_trend_service import assess_conditions_trend
from app.services.dew_risk_service import assess_dew_risk
from app.services.night_rating_service import calculate_night_rating
from app.services.opportunity_score_service import calculate_opportunity_score
from app.services.planner_service import get_tonight_plan
from app.services.scheduler_service import build_tonight_schedule
from app.services.session_checklist_service import build_session_checklist
from app.services.hosted_account_service import get_planning_context
from app.services.hosted_account_service import get_primary_observatory
from app.services.hosted_account_service import MissingObservatoryError
from app.services.hosted_recommendation_service import (
    create_recommendation_run,
)
from app.services.target_service import build_catalog_target_response
from app.services.target_service import build_target_response
from app.services.target_art_library_service import resolve_target_artwork


router = APIRouter(prefix="/tonight", tags=["Tonight"])


def _build_operator_message(schedule: Dict) -> str:
    decision = schedule["decision"]
    weather = schedule["weather"]
    rating = weather.get("observing_rating")

    if decision == "Proceed":
        return (
            "Conditions currently support imaging. Review the advisory "
            "timeline before starting."
        )

    if decision == "Use Caution":
        return (
            f"Use caution: the imaging-start weather rating is {rating}/5. "
            "Verify live conditions before opening the observatory."
        )

    reasons = []
    planned_conditions_used = any(
        weather.get(field) is not None
        for field in (
            "planned_cloud_cover_percent",
            "planned_humidity_percent",
            "planned_wind_speed_mph",
        )
    )
    cloud_cover = weather.get(
        "planned_cloud_cover_percent",
        weather.get("cloud_cover_percent"),
    )
    humidity = weather.get(
        "planned_humidity_percent",
        weather.get("humidity_percent"),
    )
    wind_speed = weather.get(
        "planned_wind_speed_mph",
        weather.get("wind_speed_mph"),
    )
    temperature_f = weather.get("planned_temperature_f")

    if rating == 0:
        reasons.append("live weather data is unavailable")
    if cloud_cover is not None and cloud_cover >= 50:
        reasons.append(f"cloud cover is {cloud_cover}%")
    if humidity is not None and humidity >= 80:
        reasons.append(f"humidity is {humidity}%")
    if wind_speed is not None and wind_speed >= 15:
        reasons.append(f"wind is {wind_speed:g} mph")
    if temperature_f is not None and temperature_f >= 105:
        reasons.append(
            f"forecast temperature near the planned start is "
            f"{temperature_f:g}°F, above Polaris's "
            "conservative heat limit"
        )
    if not reasons:
        reasons.append(f"the weather rating is {rating}/5")

    prefix = "Do not image: "
    if planned_conditions_used:
        prefix += "forecast near the imaging-window opening indicates "
    return prefix + ", ".join(reasons) + "."


def _build_legacy_target(
    db,
    planner_target: Optional[Dict],
    *,
    use_capture_history: bool = True,
    rig_profile_key: Optional[str] = None,
) -> Optional[Dict]:
    if planner_target is None:
        return None

    target = (
        build_target_response(
            db=db,
            target_name=planner_target["advisor"]["object"],
        )
        if use_capture_history
        else build_catalog_target_response(
            planner_target["advisor"]["object"]
        )
    )
    target.update(
        {
            "observable": planner_target["observable"],
            "current_altitude": planner_target["current_altitude"],
            "altitude_at_dark_midpoint": planner_target.get(
                "altitude_at_dark_midpoint"
            ),
            "maximum_dark_altitude": planner_target.get(
                "maximum_dark_altitude"
            ),
            "average_dark_altitude": planner_target.get(
                "average_dark_altitude"
            ),
            "target_geometry": planner_target.get("target_geometry"),
            "usable_dark_minutes": planner_target.get(
                "usable_dark_minutes"
            ),
            "usable_dark_hours": planner_target.get(
                "usable_dark_hours"
            ),
            "transit_time": planner_target["transit_time"],
            "moon_warning": planner_target["moon_warning"],
            "recommended_start": planner_target["recommended_start"],
            "recommended_end": planner_target["recommended_end"],
            "moon_separation_degrees": planner_target[
                "moon_separation_degrees"
            ],
            "reason": planner_target["selection_reason"],
        }
    )
    target["rig_fit"] = _build_rig_fit_summary(
        target["object"],
        rig_profile_key,
    )
    target["artwork"] = resolve_target_artwork(
        target.get("object"),
        common_name=target.get("common_name"),
        target_type=target.get("target_type"),
    )
    return target


def _build_rig_fit_summary(
    target_name: str,
    rig_profile_key: Optional[str],
) -> Optional[Dict]:
    if not rig_profile_key:
        return None

    rig = get_rig_profile(rig_profile_key)
    if rig is None:
        return None

    target_size = get_target_angular_size(target_name)
    target_width = target_size[0] if target_size else None
    target_height = target_size[1] if target_size else None
    fit = rig.assess_target_fit(target_width, target_height)
    display_rig_name = _display_rig_name(rig.manufacturer, rig.model)
    match_summary = _build_rig_match_summary(
        target_name=target_name,
        rig_label=display_rig_name,
        target_width=target_width,
        target_height=target_height,
        fit_label=fit.label,
        fit_reason=fit.reason,
    )
    return {
        "rig_key": rig.key,
        "rig_label": f"{rig.manufacturer} {rig.model}",
        "target_width_degrees": target_width,
        "target_height_degrees": target_height,
        "fits": fit.fits,
        "label": fit.label,
        "reason": fit.reason,
        "data_status": fit.data_status,
        "framing_fov_degrees": rig.framing_fov_degrees,
        "framing_fov_source": rig.framing_fov_source,
        "match_summary": match_summary,
        "margin_degrees": fit.margin_degrees,
    }


def _display_rig_name(manufacturer: str, model: str) -> str:
    if manufacturer.upper() == "DWARFLAB":
        return model.replace("DWARF", "Dwarf").replace("mini", "Mini")
    if manufacturer.upper() == "ZWO" and model.lower().startswith("seestar"):
        return model
    return f"{manufacturer} {model}"


def _build_rig_match_summary(
    *,
    target_name: str,
    rig_label: str,
    target_width: Optional[float],
    target_height: Optional[float],
    fit_label: str,
    fit_reason: str,
) -> str:
    target = target_name.strip().upper()
    common_target_names = {
        "C 20": "a wide emission nebula",
        "M8": "a bright emission nebula",
        "M16": "an emission nebula",
        "M17": "an emission nebula",
        "M20": "a nebula target",
        "M27": "a compact nebula",
        "M31": "a very large galaxy",
        "M51": "a compact galaxy",
        "M57": "a very small planetary nebula",
        "M63": "a compact galaxy",
        "M64": "a compact galaxy",
        "M97": "a compact planetary nebula",
    }
    target_description = common_target_names.get(target, "tonight's target")

    if target_width is None or target_height is None:
        return (
            f"Polaris selected {target_name} for {rig_label} because it is "
            f"{target_description} with a usable window and recommended "
            "settings for this smart-telescope workflow. Framing is not "
            "shown because Polaris does not yet have a "
            "reliable angular size for this target."
        )

    if fit_label == "Unknown fit":
        return (
            f"Polaris selected {target_name} for {rig_label} because it is "
            f"{target_description} with a usable window and recommended "
            "settings for this smart-telescope workflow. Framing is not yet "
            "supported because the rig profile lacks enough reliable optical "
            "data."
        )

    return (
        f"Polaris selected {target_name} for {rig_label} because it is "
        f"{target_description}, has a usable imaging window, and the rig "
        f"framing check is {fit_label.lower()}. {fit_reason}"
    )


def _select_backup_plan(planner: Dict) -> Optional[Dict]:
    alternatives = planner.get("alternatives") or []

    if planner.get("recommended_target") is not None:
        return alternatives[0] if alternatives else None

    return planner.get("best_theoretical_target")


def _build_legacy_night_plan(
    schedule: Dict,
    backup_target: Optional[Dict],
) -> Dict:
    backup_option = None

    if backup_target is not None:
        backup_option = {
            "object": backup_target["object"],
            "start": backup_target["recommended_start"],
            "end": backup_target["recommended_end"],
            "reason": backup_target["reason"],
        }

    return {
        "decision": schedule["decision"],
        "overall_rating": (
            schedule["weather"].get("observing_rating") or 0
        ),
        "start_imaging": schedule["darkness"][
            "astronomical_darkness_start"
        ],
        "shutdown_time": schedule["darkness"][
            "astronomical_darkness_end"
        ],
        "target_sequence": [
            {
                "object": block["object"],
                "start": block["start"],
                "end": block["end"],
                "reason": block["reason"],
            }
            for block in schedule["blocks"]
        ],
        "backup_option": backup_option,
        "notes": schedule["notes"],
    }


def _build_tonight_payload(
    current_user: CurrentUser,
    db: Session,
    *,
    equatorial_mode_enabled: bool = False,
):
    try:
        observatory = get_planning_context(
            db,
            current_user=current_user,
        )
    except MissingObservatoryError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    use_capture_history = current_user.auth_mode == "local"
    planner = get_tonight_plan(
        db,
        observatory=observatory,
        use_capture_history=use_capture_history,
        equatorial_mode_enabled=equatorial_mode_enabled,
    )
    schedule = build_tonight_schedule(
        planner,
        timezone_name=observatory.timezone_name,
        rig_profile_key=observatory.rig_profile_key,
    )
    recommended_target = _build_legacy_target(
        db,
        planner.get("recommended_target"),
        use_capture_history=use_capture_history,
        rig_profile_key=observatory.rig_profile_key,
    )
    backup_target = _build_legacy_target(
        db,
        _select_backup_plan(planner),
        use_capture_history=use_capture_history,
        rig_profile_key=observatory.rig_profile_key,
    )
    rig_profile = get_rig_profile(observatory.rig_profile_key or "")
    opportunity_target = recommended_target or backup_target
    dew_window_target = (
        planner.get("recommended_target")
        or planner.get("best_theoretical_target")
    )
    dew_risk = assess_dew_risk(
        planner["weather"],
        planned_start=(
            dew_window_target.get("recommended_start")
            if dew_window_target
            else None
        ),
        planned_end=(
            dew_window_target.get("recommended_end")
            if dew_window_target
            else None
        ),
    )
    conditions_trend = assess_conditions_trend(
        planner["weather"],
        planned_start=(
            dew_window_target.get("recommended_start")
            if dew_window_target
            else None
        ),
        planned_end=(
            dew_window_target.get("recommended_end")
            if dew_window_target
            else None
        ),
    )

    return {
        "date": schedule["date"],
        "observatory": {
            "name": observatory.name,
            "postal_code": observatory.postal_code,
            "timezone": observatory.timezone_name,
            "latitude": observatory.latitude,
            "longitude": observatory.longitude,
            "elevation_meters": observatory.elevation_meters,
            "rig_profile_key": rig_profile.key if rig_profile else None,
            "rig_profile_label": (
                _display_rig_name(rig_profile.manufacturer, rig_profile.model)
                if rig_profile
                else None
            ),
        },
        "recommended_target": recommended_target,
        "backup_target": backup_target,
        "moon": planner["moon"],
        "weather": planner["weather"],
        "night_rating": calculate_night_rating(
            planner["weather"],
            planner["moon"],
            recommended_target,
        ),
        "opportunity_score": calculate_opportunity_score(
            weather=planner["weather"],
            moon=planner["moon"],
            darkness=planner["darkness"],
            target=opportunity_target,
        ),
        "dew_risk": dew_risk,
        "conditions_trend": conditions_trend,
        "session_checklist": build_session_checklist(
            schedule=schedule,
            recommended_target=recommended_target,
            backup_target=backup_target,
            dew_risk=dew_risk,
            timezone_name=observatory.timezone_name,
        ),
        "message": _build_operator_message(schedule),
        "night_plan": _build_legacy_night_plan(
            schedule,
            backup_target,
        ),
        "darkness": planner["darkness"],
        "schedule": schedule,
    }


@router.get("", response_model=TonightResponse)
def tonight(
    equatorial_mode_enabled: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    return _build_tonight_payload(
        current_user,
        db,
        equatorial_mode_enabled=equatorial_mode_enabled,
    )


@router.post("", response_model=TonightResponse)
def create_tonight_recommendation(
    equatorial_mode_enabled: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    payload = _build_tonight_payload(
        current_user,
        db,
        equatorial_mode_enabled=equatorial_mode_enabled,
    )
    if current_user.auth_mode == "local":
        return payload

    observatory = get_primary_observatory(
        db,
        user_id=current_user.user_id,
    )
    if observatory is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Add an observing home before requesting tonight's plan."
            ),
        )
    run = create_recommendation_run(
        db,
        user_id=current_user.user_id,
        observatory=observatory,
        payload=payload,
    )
    payload["recommendation_run_id"] = run.id
    return payload
