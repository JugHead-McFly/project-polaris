from fastapi import APIRouter

from app.database.database import SessionLocal
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
def get_planner_for_tonight():
    db = SessionLocal()

    try:
        return get_tonight_plan(
            db=db
        )

    finally:
        db.close()