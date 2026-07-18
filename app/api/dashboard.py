from fastapi import APIRouter, Query

from app.database.database import SessionLocal
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import build_dashboard_response


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(include_all_history: bool = Query(default=False)):
    db = SessionLocal()

    try:
        return build_dashboard_response(
            db,
            include_all_history=include_all_history,
        )
    finally:
        db.close()
