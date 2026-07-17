from typing import Dict, Optional

from fastapi import APIRouter

from app.core.observatory import DEFAULT_POSTAL_CODE
from app.core.observatory import ELEVATION_METERS
from app.core.observatory import LATITUDE
from app.core.observatory import LONGITUDE
from app.core.observatory import OBSERVATORY_NAME
from app.core.observatory import TIMEZONE
from app.database.database import SessionLocal
from app.schemas.tonight import TonightResponse
from app.services.night_rating_service import calculate_night_rating
from app.services.planner_service import get_tonight_plan
from app.services.scheduler_service import build_tonight_schedule
from app.services.target_service import build_target_response


router = APIRouter(prefix="/tonight", tags=["Tonight"])


def _build_legacy_target(
    db,
    planner_target: Optional[Dict],
) -> Optional[Dict]:
    if planner_target is None:
        return None

    target = build_target_response(
        db=db,
        target_name=planner_target["advisor"]["object"],
    )
    target.update(
        {
            "observable": planner_target["observable"],
            "current_altitude": planner_target["current_altitude"],
            "transit_time": planner_target["transit_time"],
            "moon_warning": planner_target["moon_warning"],
            "recommended_start": planner_target["recommended_start"],
            "recommended_end": planner_target["recommended_end"],
            "moon_separation_degrees": planner_target[
                "moon_separation_degrees"
            ],
            "reason": planner_target["selection_reason"],
        }
    )
    return target


def _select_backup_plan(planner: Dict) -> Optional[Dict]:
    alternatives = planner.get("alternatives") or []

    if planner.get("recommended_target") is not None:
        return alternatives[0] if alternatives else None

    return planner.get("best_theoretical_target")


def _build_legacy_night_plan(
    schedule: Dict,
    backup_target: Optional[Dict],
) -> Dict:
    backup_option = None

    if backup_target is not None:
        backup_option = {
            "object": backup_target["object"],
            "start": backup_target["recommended_start"],
            "end": backup_target["recommended_end"],
            "reason": backup_target["reason"],
        }

    return {
        "decision": schedule["decision"],
        "overall_rating": (
            schedule["weather"].get("observing_rating") or 0
        ),
        "start_imaging": schedule["darkness"][
            "astronomical_darkness_start"
        ],
        "shutdown_time": schedule["darkness"][
            "astronomical_darkness_end"
        ],
        "target_sequence": [
            {
                "object": block["object"],
                "start": block["start"],
                "end": block["end"],
                "reason": block["reason"],
            }
            for block in schedule["blocks"]
        ],
        "backup_option": backup_option,
        "notes": schedule["notes"],
    }


@router.get("", response_model=TonightResponse)
def tonight():
    db = SessionLocal()

    try:
        planner = get_tonight_plan(db)
        schedule = build_tonight_schedule(planner)
        recommended_target = _build_legacy_target(
            db,
            planner.get("recommended_target"),
        )
        backup_target = _build_legacy_target(
            db,
            _select_backup_plan(planner),
        )

        return {
            "date": schedule["date"],
            "observatory": {
                "name": OBSERVATORY_NAME,
                "postal_code": DEFAULT_POSTAL_CODE,
                "timezone": TIMEZONE,
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "elevation_meters": ELEVATION_METERS,
            },
            "recommended_target": recommended_target,
            "backup_target": backup_target,
            "moon": planner["moon"],
            "weather": planner["weather"],
            "night_rating": calculate_night_rating(
                planner["weather"],
                planner["moon"],
                recommended_target,
            ),
            "message": (
                "Planner V3 advisory schedule generated: "
                f"{schedule['decision']}."
            ),
            "night_plan": _build_legacy_night_plan(
                schedule,
                backup_target,
            ),
            "darkness": planner["darkness"],
            "schedule": schedule,
        }

    finally:
        db.close()
