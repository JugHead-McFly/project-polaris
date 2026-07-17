from fastapi import APIRouter

from app.database.database import SessionLocal
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import build_dashboard_response


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard():
    db = SessionLocal()

    try:
        return build_dashboard_response(db)
    finally:
        db.close()
