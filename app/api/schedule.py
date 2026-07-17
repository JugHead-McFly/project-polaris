from fastapi import APIRouter

from app.database.database import SessionLocal
from app.schemas.schedule import TonightScheduleResponse
from app.services.scheduler_service import get_tonight_schedule


router = APIRouter(prefix="/planner", tags=["Planner"])


@router.get("/schedule", response_model=TonightScheduleResponse)
def get_schedule_for_tonight():
    db = SessionLocal()

    try:
        return get_tonight_schedule(db)
    finally:
        db.close()
