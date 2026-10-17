from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.database.database import get_tenant_db
from app.schemas.target import TargetSummary
from app.services.target_service import build_target_response


router = APIRouter(
    prefix="/objects",
    tags=["Objects"],
)


@router.get("/catalog/search")
def search_catalog(q: str = Query(default="", max_length=100),
                   offset: int = Query(default=0, ge=0),
                   limit: int = Query(default=30, ge=1, le=100),
                   rig_profile_key: str = Query(default="", max_length=80)):
    from app.services.deep_sky_catalog import search, automatic_exclusion
    from app.data.rig_profiles import get_rig_profile
    rig = get_rig_profile(rig_profile_key)
    result = search(q, offset, limit)
    result["items"] = [dict(entry) for entry in result["items"]]
    for entry in result["items"]:
        major, minor = entry["major_arcmin"], entry["minor_arcmin"]
        fit = rig.assess_target_fit(major/60, (minor or major)/60).fits if rig and major else None
        entry.update(single_frame_fit=fit, mosaic_required=fit is False,
                     automatic_discovery_exclusion=automatic_exclusion(entry, rig),
                     extent_is_bounding_circle=major is not None and minor is None)
    return result


@router.get(
    "/{object_name}",
    response_model=TargetSummary,
    responses={
        404: {
            "description": "Target not found",
        }
    },
)
def get_object_summary(
    object_name: str = Path(
        ...,
        title="Target name",
        description=(
            "Astronomical target designation, "
            "for example M17, M51, or NGC6633."
        ),
        examples=["M17"],
    ),
    db: Session = Depends(get_tenant_db),
):
    normalized_name = object_name.strip().upper()

    try:
        return build_target_response(
            db=db,
            target_name=normalized_name,
        )

    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Target '{normalized_name}' "
                "was not found."
            ),
        )
