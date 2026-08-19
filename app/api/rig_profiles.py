from fastapi import APIRouter

from app.schemas.rig_profile import RigProfileCatalogResponse
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
