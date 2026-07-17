from fastapi import APIRouter

from app.database.database import SessionLocal
from app.schemas.system import SystemStatusResponse
from app.services.system_service import build_system_status


router = APIRouter(prefix="/system", tags=["System"])


@router.get("", response_model=SystemStatusResponse)
def system_status():
    db = SessionLocal()

    try:
        return build_system_status(db)
    finally:
        db.close()
