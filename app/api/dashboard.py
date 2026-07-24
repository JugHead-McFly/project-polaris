from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import build_dashboard_response


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(
    include_all_history: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return build_dashboard_response(
        db,
        include_all_history=include_all_history,
    )
