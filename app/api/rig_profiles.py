from fastapi import APIRouter, HTTPException, Path, Query

from app.schemas.rig_profile import RigProfileCatalogResponse
from app.schemas.rig_profile import RigProfileDetailResponse
from app.schemas.rig_profile import RigTargetFitResponse
from app.data.rig_profiles import get_rig_profile
from app.services.rig_profile_service import list_rig_profile_summaries
from app.services.rig_profile_service import summarize_rig_profile_catalog


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
    }
