from datetime import datetime

from fastapi import APIRouter

from app.database.database import SessionLocal
from app.models import Capture
from app.services.portfolio_service import TARGET_PRIORITY
from app.services.portfolio_service import build_portfolio_target
from app.services.recommendation_service import get_backup_reason
from app.services.recommendation_service import get_recommendation_reason
from app.services.recommendation_service import get_recommended_targets
from app.core.observatory import DEFAULT_POSTAL_CODE
from app.core.observatory import OBSERVATORY_NAME
from app.core.observatory import TIMEZONE
from app.core.observatory import ELEVATION_METERS
from app.core.observatory import LATITUDE
from app.core.observatory import LONGITUDE
from app.services.astronomy_service import get_altitude
from app.services.astronomy_service import is_observable
from app.services.astronomy_service import get_transit_time
from app.services.astronomy_service import get_recommended_window
from app.services.astronomy_service import get_moon_info
from app.services.astronomy_service import get_moon_separation
from app.services.astronomy_service import get_moon_warning
from app.services.astronomy_service import get_darkness_info
from app.services.weather_service import get_weather_summary
from app.services.night_rating_service import calculate_night_rating
from app.schemas.tonight import TonightResponse
from app.services.night_planner_service import (
    build_night_plan,
)

router = APIRouter(prefix="/tonight", tags=["Tonight"])


@router.get("", response_model=TonightResponse)
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

            recommended_target["current_altitude"] = get_altitude(
                recommended_target["object"]
            )
            recommended_target["observable"] = is_observable(
                recommended_target["object"]
            )
            recommended_target["transit_time"] = get_transit_time(
                recommended_target["object"]
            )

            window = get_recommended_window(
                recommended_target["object"]
            )

            recommended_target["recommended_start"] = (
                window["recommended_start"]
            )
            recommended_target["recommended_end"] = (
                window["recommended_end"]
            )
            target_name = recommended_target["object"]

            recommended_target["moon_separation_degrees"] = (
                get_moon_separation(target_name)
            )

            recommended_target["moon_warning"] = get_moon_warning(
                recommended_target["object"]
            )

        else:
            recommended_target = None

        if backup_name:
            backup_target = portfolio[backup_name].copy()

            backup_target["current_altitude"] = get_altitude(
                backup_target["object"]
            )
            backup_target["observable"] = is_observable(
                backup_target["object"]
            )
            backup_target["transit_time"] = get_transit_time(
                backup_target["object"]
            )

            window = get_recommended_window(
                backup_target["object"]
            )

            backup_target["recommended_start"] = (
                window["recommended_start"]
            )
            backup_target["recommended_end"] = (
                window["recommended_end"]
            )

            backup_target["moon_warning"] = (
                get_moon_warning(
                    backup_target["object"]
                )
            )
            target_name = backup_target["object"]

            backup_target["moon_separation_degrees"] = (
                get_moon_separation(target_name)
            ) 
        else:
            backup_target = None

        moon = get_moon_info()
        weather = get_weather_summary(DEFAULT_POSTAL_CODE)

        night_rating = calculate_night_rating(
            weather,
            moon,
            recommended_target,
        )

        darkness = get_darkness_info()

        night_plan = build_night_plan(
            recommended_target,
            backup_target,
            darkness,
            weather,
        )

        
        return {
            "date": datetime.now().date().isoformat(),
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
            "moon": moon,
            "weather": weather,
            "night_rating": night_rating,
            "message": "Astronomy calculations coming soon.",
            "night_plan": night_plan,
            "darkness": darkness,
        }

    finally:
        db.close()