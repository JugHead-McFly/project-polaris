"""User's continuous best-target policy, isolated from observations/providers."""
from datetime import timedelta
from unittest.mock import patch

import pytest

from import_plan_fixture import START, END
from test_full_night_schedule import target
from app.services.scheduler_service import build_schedule_blocks, build_tonight_schedule
from app.services.planner_service import get_dark_visibility
from app.services.advisor_service import get_catalog_exposure_advice
from import_plan_fixture import workflow, manifest
from fastapi.testclient import TestClient


def test_best_finite_goal_runs_continuously_then_next_best():
    blocks = build_schedule_blocks([
        target("best", START, END, score=100, remaining_seconds=3*3600, exposure=30),
        target("sets-soon", START, START+timedelta(hours=2), score=60),
        target("rising", START+timedelta(minutes=30), END, score=110, remaining_seconds=2*3600, exposure=30),
        target("last", START, END, score=50),
    ], timezone_name="UTC", rig_profile_key="unknown")
    assert [b["object"] for b in blocks] == ["best", "rising", "last"]
    assert blocks[0]["imaging_minutes"] == 180
    assert blocks[1]["imaging_minutes"] == 120
    assert sum(b["duration_minutes"] for b in blocks) == 480
    assert all(a["end_at"] == b["start_at"] for a, b in zip(blocks, blocks[1:]))


def test_more_than_four_targets_are_explicit_not_truncated():
    candidates = [target(str(i), START, END, score=100-i, remaining_seconds=3600) for i in range(7)]
    result = build_tonight_schedule({"decision": "Proceed", "notes": [], "schedule_candidates": candidates,
        "recommended_target": candidates[0], "alternatives": [], "weather": {}, "moon": {},
        "darkness": {"astronomical_darkness_start": START.isoformat(), "astronomical_darkness_end": END.isoformat()}}, timezone_name="UTC")
    assert len(result["blocks"]) == 7
    assert any("7 targets" in note and "not a hard cutoff" in note for note in result["notes"])
    assert all(b["imaging_minutes"] == 60 for b in result["blocks"])


@pytest.mark.parametrize("rising", [True, False])
def test_35_degree_crossing_refined_to_one_minute(rising):
    def altitude(**kw):
        return [35 + ((at-START).total_seconds()/60 - 22.5) * (1 if rising else -1)
                for at in kw["observation_datetimes"]]
    with patch("app.services.planner_service.get_altitudes_at", side_effect=altitude):
        visibility = get_dark_visibility("M31", START, START+timedelta(hours=1))
    boundary = visibility["recommended_start_datetime" if rising else "recommended_end_datetime"]
    assert boundary == START+timedelta(minutes=23 if rising else 22)


def test_visible_completed_mosaic_explains_gap_without_fake_imaging():
    candidate = target("M31", START, END, remaining_seconds=0)
    candidate["mosaic_required"] = True
    planner = {"decision": "Proceed", "notes": [], "recommended_target": candidate, "alternatives": [],
               "weather": {}, "moon": {}, "darkness": {"astronomical_darkness_start": START.isoformat(),
               "astronomical_darkness_end": END.isoformat()}}
    result = build_tonight_schedule(planner, timezone_name="UTC")
    assert result["blocks"] == []
    assert "M31" in result["gaps"][0]["reason"]
    candidate["advisor"]["remaining_seconds"] = 3600
    result = build_tonight_schedule(planner, timezone_name="UTC")
    assert result["unscheduled_dark_minutes"] == 0
    assert result["blocks"][0]["opportunity_only"]
    assert result["blocks"][0]["imaging_minutes"] == 0
    assert result["blocks"][0]["planned_subframes"] is None


def test_hosted_short_final_goal_is_admitted_before_scheduler():
    def visibility(*args, **kwargs):
        return {"known_position": True, "usable_dark_minutes": 20, "usable_dark_hours": 1/3,
                "maximum_dark_altitude": 60, "average_dark_altitude": 50,
                "recommended_start_datetime": START,
                "recommended_end_datetime": START+timedelta(minutes=20), "target_geometry": None}
    goal = get_catalog_exposure_advice("M27")["goal_hours"]
    with workflow() as flow, patch("app.services.planner_service.TARGETS", ["M27"]), \
            patch("app.services.planner_service.get_dark_visibility", visibility), TestClient(flow.app) as client:
        assert flow.sync(client, manifest(goal-1/6)).status_code == 200
        schedule = flow.plan(client)["schedule"]
    assert len(schedule["blocks"]) == 1
    assert schedule["blocks"][0]["object"] == "M27"
    assert 0 < schedule["blocks"][0]["imaging_minutes"] <= 10
