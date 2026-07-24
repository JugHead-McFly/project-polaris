from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.schedule import TonightScheduleResponse
from app.services.scheduler_service import get_tonight_schedule


router = APIRouter(prefix="/planner", tags=["Planner"])


@router.get("/schedule", response_model=TonightScheduleResponse)
def get_schedule_for_tonight(db: Session = Depends(get_db)):
    return get_tonight_schedule(db)
