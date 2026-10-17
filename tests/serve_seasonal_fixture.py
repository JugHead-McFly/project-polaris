"""Local Phoenix Oct17 preview: real sky, synthetic weather/history, memory DB."""
from serve_import_plan_fixture import add_browser_fixture
from import_plan_fixture import workflow
from datetime import datetime
from unittest.mock import patch
from astropy.utils import iers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import uvicorn
from app.core.planning_context import ObservatoryContext
from app.services import astronomy_service as astronomy, planner_service as planner
from app.services.advisor_service import get_catalog_exposure_advice
from app.api.objects import router as objects_router


if __name__ == "__main__":
    iers.conf.auto_download = False
    context = ObservatoryContext(name="Synthetic Phoenix Oct17", latitude=33.4484, longitude=-112.074,
        timezone_name="America/Phoenix", elevation_meters=331, bortle_class=8, rig_profile_key="dwarf-mini")
    reference = datetime.fromisoformat("2026-10-17T19:00:00+00:00")
    weather = dict(observing_rating=5, cloud_cover_percent=0, humidity_percent=30,
        wind_speed_mph=2, temperature_f=65, cache_status="fresh", status="Synthetic clear weather")
    history = {"M31": {"seconds": get_catalog_exposure_advice("M31")["goal_hours"]*3600}}
    with Session(create_engine("sqlite:///:memory:")) as db, \
            patch.object(planner, "get_weather_summary", return_value=weather), \
            patch.object(planner, "get_darkness_info", side_effect=lambda **kw: astronomy.get_darkness_info(reference_datetime=reference, **kw)), \
            patch.object(planner, "get_darkness_window_datetimes", side_effect=lambda **kw: astronomy.get_darkness_window_datetimes(reference_datetime=reference, **kw)), \
            patch.object(planner, "get_moon_info", side_effect=lambda **kw: astronomy.get_moon_info_at(reference, **kw)):
        plan = planner.get_tonight_plan(db, observatory=context, use_capture_history=False, capture_progress=history)
    with workflow() as flow, \
            patch("app.api.tonight.get_tonight_plan", return_value=plan), \
            patch("app.api.tonight.get_planning_context", return_value=context):
        flow.app.include_router(objects_router)
        add_browser_fixture(flow)
        uvicorn.run(flow.app, host="127.0.0.1", port=8113, access_log=False)
