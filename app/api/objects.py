from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database.database import get_tenant_db
from app.schemas.target import TargetSummary
from app.services.target_service import build_target_response


router = APIRouter(
    prefix="/objects",
    tags=["Objects"],
)


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
