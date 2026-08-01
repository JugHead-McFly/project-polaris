from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.database.database import get_tenant_db
from app.schemas.planner import TonightPlannerResponse
from app.services.hosted_account_service import get_planning_context
from app.services.hosted_account_service import MissingObservatoryError
from app.services.planner_service import (
    get_tonight_plan,
)


router = APIRouter(
    prefix="/planner",
    tags=["Planner"],
)


@router.get(
    "/tonight",
    response_model=TonightPlannerResponse,
)
def get_planner_for_tonight(
    equatorial_mode_enabled: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
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
    return get_tonight_plan(
        db=db,
        observatory=observatory,
        use_capture_history=current_user.auth_mode == "local",
        equatorial_mode_enabled=equatorial_mode_enabled,
    )
