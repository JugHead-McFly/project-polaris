from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_tenant_db
from app.schemas.planner import TonightPlannerResponse
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
def get_planner_for_tonight(db: Session = Depends(get_tenant_db)):
    return get_tonight_plan(db=db)
