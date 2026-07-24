from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_tenant_db
from app.schemas.system import SystemStatusResponse
from app.services.system_service import build_system_status


router = APIRouter(prefix="/system", tags=["System"])


@router.get("", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_tenant_db)):
    return build_system_status(db)
