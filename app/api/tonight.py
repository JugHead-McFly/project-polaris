from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.database.database import get_tenant_db
from app.schemas.tonight import TonightResponse
from app.data.rig_profiles import get_rig_profile
from app.data.targets import get_target_angular_size
from app.services.night_rating_service import calculate_night_rating
from app.services.planner_service import get_tonight_plan
from app.services.scheduler_service import build_tonight_schedule
from app.services.hosted_account_service import get_planning_context
from app.services.hosted_account_service import get_primary_observatory
from app.services.hosted_account_service import MissingObservatoryError
from app.services.hosted_recommendation_service import (
    create_recommendation_run,
)
from app.services.target_service import build_catalog_target_response
from app.services.target_service import build_target_response


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

    return "Do not image: " + ", ".join(reasons) + "."


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
    return {
        "rig_key": rig.key,
        "rig_label": f"{rig.manufacturer} {rig.model}",
        "target_width_degrees": target_width,
        "target_height_degrees": target_height,
        "fits": fit.fits,
        "label": fit.label,
        "reason": fit.reason,
        "margin_degrees": fit.margin_degrees,
    }


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
                f"{rig_profile.manufacturer} {rig_profile.model}"
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
