from datetime import datetime

from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture
from app.services.portfolio_service import TARGET_PRIORITY
from app.services.portfolio_service import build_portfolio_target
from app.services.recommendation_service import get_backup_reason
from app.services.recommendation_service import get_recommendation_reason
from app.services.recommendation_service import get_recommended_targets

router = APIRouter(prefix="/tonight", tags=["Tonight"])


@router.get("")
def tonight():
    db = SessionLocal()

    try:
        integration_by_object = {}

        captures = db.query(Capture).all()

        for capture in captures:
            if not capture.object_name:
                continue

            integration_by_object[capture.object_name] = (
                integration_by_object.get(capture.object_name, 0)
                + (capture.exposure_seconds or 0)
            )

        portfolio = {
            target: build_portfolio_target(
                object_name=target,
                total_hours=round(
                    integration_by_object.get(target, 0) / 3600,
                    2,
                ),
            )
            for target in TARGET_PRIORITY
        }

        recommended_name, backup_name = get_recommended_targets(portfolio)

        if recommended_name:
            recommended_target = portfolio[recommended_name].copy()
            recommended_target["reason"] = (
                get_recommendation_reason(recommended_name)
            )
        else:
            recommended_target = None

        if backup_name:
            backup_target = portfolio[backup_name].copy()
            backup_target["reason"] = (
                get_backup_reason(backup_name)
            )
        else:
            backup_target = None
            
        return {
            "date": datetime.now().date().isoformat(),
            "recommended_target": recommended_target,
            "backup_target": backup_target, 
            "moon": None,
            "weather": None,
            "message": "Astronomy calculations coming soon.",
        }

    finally:
        db.close()