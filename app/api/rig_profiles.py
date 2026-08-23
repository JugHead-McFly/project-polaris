from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query

from app.schemas.rig_profile import RigProfileCatalogResponse
from app.schemas.rig_profile import RigProfileDetailResponse
from app.schemas.rig_profile import RigRunPlanResponse
from app.schemas.rig_profile import RigTargetScoreResponse
from app.schemas.rig_profile import RigTargetFitResponse
from app.data.rig_profiles import get_rig_profile
from app.services.rig_profile_service import list_rig_profile_summaries
from app.services.rig_profile_service import summarize_rig_profile_catalog
from app.services.target_scoring_service import score_target_opportunity_for_rig


router = APIRouter(prefix="/rig-profiles", tags=["Rig Profiles"])


@router.get("", response_model=RigProfileCatalogResponse)
def list_rig_profiles():
    catalog = summarize_rig_profile_catalog()
    profiles = list_rig_profile_summaries()
    return {
        "total_profiles": catalog.total_profiles,
        "manufacturers": catalog.manufacturers,
        "profiles_with_field_of_view": catalog.profiles_with_field_of_view,
        "profiles_with_battery_limit": catalog.profiles_with_battery_limit,
        "profiles_with_storage_limit": catalog.profiles_with_storage_limit,
        "profiles_with_temperature_limit": catalog.profiles_with_temperature_limit,
        "profiles_with_frame_limit": catalog.profiles_with_frame_limit,
        "profiles": profiles,
    }


@router.get(
    "/{rig_key}",
    response_model=RigProfileDetailResponse,
    responses={404: {"description": "Rig profile not found"}},
)
def get_rig_profile_detail(
    rig_key: str = Path(
        ...,
        title="Rig key or model",
        description="Rig profile key or model name, for example dwarf-3 or Seestar S50.",
        examples=["dwarf-3"],
    )
):
    profile = get_rig_profile(rig_key)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rig profile '{rig_key}' was not found.",
        )
    return profile


@router.get(
    "/{rig_key}/fit-check",
    response_model=RigTargetFitResponse,
    responses={404: {"description": "Rig profile not found"}},
)
def check_target_fit_for_rig(
    rig_key: str = Path(
        ...,
        title="Rig key or model",
        description="Rig profile key or model name, for example dwarf-3 or Seestar S50.",
        examples=["dwarf-3"],
    ),
    target_width_degrees: float = Query(
        ...,
        gt=0,
        description="Target angular width in degrees.",
        examples=[2.0],
    ),
    target_height_degrees: float = Query(
        ...,
        gt=0,
        description="Target angular height in degrees.",
        examples=[1.0],
    ),
):
    profile = get_rig_profile(rig_key)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rig profile '{rig_key}' was not found.",
        )
    fit = profile.assess_target_fit(target_width_degrees, target_height_degrees)
    return {
        "rig_key": profile.key,
        "target_width_degrees": target_width_degrees,
        "target_height_degrees": target_height_degrees,
        "fits": fit.fits,
        "label": fit.label,
        "margin_degrees": fit.margin_degrees,
        "reason": fit.reason,
        "data_status": fit.data_status,
        "framing_fov_degrees": profile.framing_fov_degrees,
        "framing_fov_source": profile.framing_fov_source,
    }


@router.get(
    "/{rig_key}/run-plan",
    response_model=RigRunPlanResponse,
    responses={404: {"description": "Rig profile not found"}},
)
def estimate_run_plan_for_rig(
    rig_key: str = Path(
        ...,
        title="Rig key or model",
        description="Rig profile key or model name, for example dwarf-3 or Seestar S50.",
        examples=["dwarf-3"],
    ),
    imaging_minutes: int = Query(
        ...,
        gt=0,
        description="Planned imaging time in minutes.",
        examples=[240],
    ),
    sub_exposure_seconds: int = Query(
        ...,
        gt=0,
        description="Sub-exposure length in seconds.",
        examples=[30],
    ),
):
    profile = get_rig_profile(rig_key)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rig profile '{rig_key}' was not found.",
        )
    plan = profile.estimate_run_plan(
        imaging_minutes=imaging_minutes,
        sub_exposure_seconds=sub_exposure_seconds,
    )
    return {
        "rig_key": profile.key,
        "imaging_minutes": imaging_minutes,
        "sub_exposure_seconds": sub_exposure_seconds,
        "total_frames": plan.total_frames,
        "run_count": plan.run_count,
        "frames_per_run": plan.frames_per_run,
        "label": plan.label,
        "reason": plan.reason,
    }


@router.get(
    "/{rig_key}/target-score",
    response_model=RigTargetScoreResponse,
    responses={404: {"description": "Rig profile not found"}},
)
def score_target_for_rig(
    rig_key: str = Path(
        ...,
        title="Rig key or model",
        description="Rig profile key or model name, for example dwarf-3 or Seestar S50.",
        examples=["dwarf-3"],
    ),
    target_width_degrees: float = Query(
        ...,
        gt=0,
        description="Target angular width in degrees.",
        examples=[2.0],
    ),
    target_height_degrees: float = Query(
        ...,
        gt=0,
        description="Target angular height in degrees.",
        examples=[1.0],
    ),
    maximum_altitude_degrees: Optional[float] = Query(
        None,
        ge=0,
        le=90,
        description="Maximum target altitude during the usable window.",
        examples=[58],
    ),
    usable_dark_minutes: int = Query(
        ...,
        ge=0,
        description="Usable dark imaging minutes.",
        examples=[210],
    ),
    moon_illumination_percent: Optional[float] = Query(
        None,
        ge=0,
        le=100,
        description="Moon illumination percentage.",
        examples=[22],
    ),
    moon_separation_degrees: Optional[float] = Query(
        None,
        ge=0,
        le=180,
        description="Moon separation from the target in degrees.",
        examples=[95],
    ),
    bortle_class: Optional[int] = Query(
        None,
        ge=1,
        le=9,
        description="Bortle sky class for the observing site.",
        examples=[4],
    ),
    exposure_confidence: Optional[float] = Query(
        None,
        ge=0,
        le=1,
        description="Experimental confidence that exposure settings are supported.",
        examples=[0.75],
    ),
):
    profile = get_rig_profile(rig_key)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rig profile '{rig_key}' was not found.",
        )
    result = score_target_opportunity_for_rig(
        rig=profile,
        target_width_degrees=target_width_degrees,
        target_height_degrees=target_height_degrees,
        maximum_altitude_degrees=maximum_altitude_degrees,
        usable_dark_minutes=usable_dark_minutes,
        moon_illumination_percent=moon_illumination_percent,
        moon_separation_degrees=moon_separation_degrees,
        bortle_class=bortle_class,
        exposure_confidence=exposure_confidence,
    )
    return {
        "rig_key": profile.key,
        "target_width_degrees": target_width_degrees,
        "target_height_degrees": target_height_degrees,
        "maximum_altitude_degrees": maximum_altitude_degrees,
        "usable_dark_minutes": usable_dark_minutes,
        "moon_illumination_percent": moon_illumination_percent,
        "moon_separation_degrees": moon_separation_degrees,
        "bortle_class": bortle_class,
        "exposure_confidence": exposure_confidence,
        "score": result.score,
        "quality": result.quality,
        "field_of_view_label": (
            profile.assess_target_fit(
                target_width_degrees,
                target_height_degrees,
            ).label
        ),
        "components": result.components,
    }
