from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Path

from app.database.database import SessionLocal
from app.schemas.advisor import (
    ExposureAdvisorResponse,
)
from app.services.advisor_service import (
    get_exposure_advice,
)


router = APIRouter(
    prefix="/advisor",
    tags=["Advisor"],
)


@router.get(
    "/{object_name}",
    response_model=ExposureAdvisorResponse,
    responses={
        404: {
            "description": "Target not found",
        }
    },
)
def get_target_advice(
    object_name: str = Path(
        ...,
        title="Target name",
        description=(
            "Astronomical target designation, "
            "for example M17, M51, or NGC6633."
        ),
        examples=["M17"],
    )
):
    db = SessionLocal()

    try:
        try:
            return get_exposure_advice(
                db=db,
                object_name=object_name,
            )

        except ValueError:
            normalized_name = (
                object_name.strip().upper()
            )

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Target '{normalized_name}' "
                    "was not found."
                ),
            )

    finally:
        db.close()