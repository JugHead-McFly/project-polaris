"""Real sky, synthetic weather/history, memory-only database."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from astropy.utils import iers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.planning_context import ObservatoryContext
from app.data.seasonal_targets import SEASONAL_TARGETS
from app.data.targets import TARGETS
from app.data.rig_profiles import get_rig_profile
from app.services import astronomy_service as astronomy, planner_service as planner
from app.services.advisor_service import get_catalog_exposure_advice
from app.services.capture_history_service import history_advice
from app.services.portfolio_service import build_portfolio_target
from app.services.scheduler_service import build_tonight_schedule, build_schedule_blocks
from test_full_night_schedule import target
from import_plan_fixture import START, END


def test_catalog_fit_and_existing_goals_preserved_without_invented_settings():
    rig = get_rig_profile("dwarf-mini")
    for name, entry in SEASONAL_TARGETS.items():
        assert rig.assess_target_fit(*entry["size"]).fits is (name != "M45")
        advice = history_advice(name, {name: {"seconds": 4*3600}})
        assert advice["remaining_seconds"] == 0
        assert advice["goal_hours"] == 4
        assert advice["recommended_sub_exposure_seconds"] is None
        assert advice["recommended_gain"] is None
        assert advice["recommended_filter"] is None
        assert build_portfolio_target(name, 4)["recommended_exposure"] is None


def test_manual_mosaic_yields_to_current_and_later_single_frame_targets():
    mosaic = target("M31", START, END, score=200)
    mosaic["mosaic_required"] = True
    single = target("M27", START+timedelta(hours=2), END, score=50)
    blocks = build_schedule_blocks([mosaic, single], timezone_name="UTC")
    assert [b["object"] for b in blocks] == ["M31", "M27"]
    assert blocks[0]["end_at"] == single["schedule_windows"][0]["start"]
    assert blocks[0]["imaging_minutes"] == 0
    single["schedule_windows"][0]["start"] = START.isoformat()
    assert build_schedule_blocks([mosaic, single], timezone_name="UTC")[0]["object"] == "M27"


@pytest.mark.parametrize("broad", [False, True])
@pytest.mark.parametrize("date", ["2026-10-17", "2026-12-15", "2027-02-15"])
def test_real_phoenix_seasonal_darkness(date, broad):
    context = ObservatoryContext(name="Synthetic Phoenix", latitude=33.4484, longitude=-112.074,
        timezone_name="America/Phoenix", elevation_meters=331, bortle_class=8, rig_profile_key="dwarf-mini")
    reference = datetime.fromisoformat(date+"T19:00:00+00:00")
    weather = dict(observing_rating=5, cloud_cover_percent=0, humidity_percent=30,
                   wind_speed_mph=2, temperature_f=65, cache_status="fresh")
    history = {"M31": {"seconds": get_catalog_exposure_advice("M31")["goal_hours"]*3600}}
    with iers.conf.set_temp("auto_download", False), Session(create_engine("sqlite:///:memory:")) as db, \
            patch.object(planner, "get_weather_summary", return_value=weather), \
            patch.object(planner, "get_darkness_info", side_effect=lambda **kw: astronomy.get_darkness_info(reference_datetime=reference, **kw)), \
            patch.object(planner, "get_darkness_window_datetimes", side_effect=lambda **kw: astronomy.get_darkness_window_datetimes(reference_datetime=reference, **kw)), \
            patch.object(planner, "get_moon_info", side_effect=lambda **kw: astronomy.get_moon_info_at(reference, **kw)):
        plan = planner.get_tonight_plan(db, observatory=context, use_capture_history=False, capture_progress=history, target_names=None if broad else list(TARGETS))
        schedule = build_tonight_schedule(plan, timezone_name=context.timezone_name, rig_profile_key=context.rig_profile_key)
        assert schedule["date"] == date
        if date == "2026-10-17" and not broad:
            assert [b["object"] for b in schedule["blocks"]] == ["NGC281", "M33", "M1"]
            assert schedule["unscheduled_dark_minutes"] < 1
        assert schedule["unscheduled_dark_minutes"] < 2
        used = {}
        for block in schedule["blocks"]:
            name = block["object"]
            assert name != "M31"
            used[name] = used.get(name, 0)+block["imaging_minutes"]*60
            assert used[name] <= get_catalog_exposure_advice(name)["remaining_seconds"]
            start, end = map(datetime.fromisoformat, (block["start_at"], block["end_at"]))
            sample = [start+timedelta(minutes=m) for m in range(int((end-start).total_seconds()/60)+1)]
            assert min(astronomy.get_altitudes_at(target_name=name, observation_datetimes=sample, observatory=context)) >= 35
            if name in SEASONAL_TARGETS:
                assert block["planned_subframes"] is None
                if not block.get("mosaic_required"):
                    assert "confirmation" in block["settings_confidence"]
        assert schedule["allocated_minutes"] + schedule["unscheduled_dark_minutes"] == pytest.approx((datetime.fromisoformat(plan["darkness"]["astronomical_darkness_end_at"])-datetime.fromisoformat(plan["darkness"]["astronomical_darkness_start_at"])).total_seconds()/60)
