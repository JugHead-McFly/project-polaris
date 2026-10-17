"""Full-night regressions use synthetic windows/history; never the live database."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from test_scheduler_service import candidate
from app.services.scheduler_service import build_schedule_blocks, build_tonight_schedule, _darkness_minutes
from app.services.planner_service import get_dark_visibility
from import_plan_fixture import workflow, START, END


def target(name, start, end, score=100, **kwargs):
    result = candidate(name, score, start.strftime("%Y-%m-%d %I:%M %p"),
                       end.strftime("%Y-%m-%d %I:%M %p"), **kwargs)
    result["schedule_windows"] = [{"start": start.isoformat(), "end": end.isoformat()}]
    return result


@pytest.mark.parametrize("night", ["2026-01-15", "2026-06-21", "2026-10-17", "2026-12-31"])
def test_eight_targets_cover_to_dawn_beyond_four_blocks_and_six_candidate_shortlist(night):
    start = datetime.fromisoformat(night + "T20:00:00+00:00")
    targets = [target(f"T{i}", start + timedelta(hours=i), start + timedelta(hours=i+1)) for i in range(8)]
    planner = {"decision": "Proceed", "notes": [], "recommended_target": targets[0],
               "alternatives": targets[1:6], "schedule_candidates": targets,
               "weather": {}, "moon": {}, "darkness": {
                   "astronomical_darkness_start": start.isoformat(),
                   "astronomical_darkness_end": (start + timedelta(hours=8)).isoformat()}}
    result = build_tonight_schedule(planner, timezone_name="UTC")
    assert len(result["blocks"]) == 8
    assert result["allocated_minutes"] == 480
    assert result["unscheduled_dark_minutes"] == 0
    assert result["gaps"] == []
    assert "end of astronomical darkness" in result["end_reason"]


def test_short_high_ranked_goal_does_not_steal_time_from_viable_target():
    end = START + timedelta(hours=3)
    blocks = build_schedule_blocks([
        target("tiny-goal", START, end, remaining_seconds=600),
        target("replacement", START, end, score=50),
    ], timezone_name="UTC")
    assert [(b["object"], b["duration_minutes"]) for b in blocks] == [("replacement", 180)]


def test_disjoint_windows_never_merge_across_obstruction_and_need_fresh_setup():
    selected = target("M31", START, END)
    selected["schedule_windows"] = [
        {"start": START.isoformat(), "end": (START + timedelta(hours=2)).isoformat()},
        {"start": (END - timedelta(hours=2)).isoformat(), "end": END.isoformat()},
    ]
    blocks = build_schedule_blocks([selected], timezone_name="UTC")
    assert [b["duration_minutes"] for b in blocks] == [120, 120]
    assert [b["setup_minutes"] for b in blocks] == [5, 5]
    assert datetime.fromisoformat(blocks[0]["end_at"]) < datetime.fromisoformat(blocks[1]["start_at"])


def test_completed_goals_and_invisible_targets_never_fill_darkness():
    blocks = build_schedule_blocks([
        target("complete", START, END, remaining_seconds=0),
        target("invisible", START, END, observable=False),
    ])
    assert blocks == []


def test_short_boundary_does_not_discard_an_allocated_block():
    blocks = build_schedule_blocks([
        target("early", START, END, score=80),
        target("later", START + timedelta(minutes=10), END, score=100),
    ], timezone_name="UTC")
    assert sum(b["duration_minutes"] for b in blocks) == 480
    assert blocks[0]["duration_minutes"] == 30


def test_finite_flexible_goal_is_reserved_for_after_early_target_sets():
    blocks = build_schedule_blocks([
        target("flexible", START, END, score=100, remaining_seconds=4*3600),
        target("sets-early", START, START + timedelta(hours=4), score=50),
    ], timezone_name="UTC")
    assert blocks[0]["object"] == "sets-early"
    assert sum(b["duration_minutes"] for b in blocks) == 480


def test_schedule_clips_to_darkness_and_reports_true_visibility_gap():
    early = target("early", START - timedelta(hours=1), START + timedelta(hours=2))
    late = target("late", END - timedelta(hours=2), END + timedelta(hours=1))
    result = build_tonight_schedule({"decision": "Proceed", "notes": [],
        "recommended_target": early, "alternatives": [late], "weather": {}, "moon": {},
        "darkness": {"astronomical_darkness_start": START.isoformat(),
                     "astronomical_darkness_end": END.isoformat()}}, timezone_name="UTC")
    assert result["allocated_minutes"] == 240
    assert result["unscheduled_dark_minutes"] == 240
    assert len(result["gaps"]) == 1
    assert result["gaps"][0]["minutes"] == 240


@pytest.mark.parametrize("start,end,minutes", [
    ("2026-11-01T00:00:00-04:00", "2026-11-01T04:00:00-05:00", 300),
    ("2026-03-08T00:00:00-05:00", "2026-03-08T04:00:00-04:00", 180),
])
def test_dst_uses_elapsed_time_and_retains_unambiguous_instants(start, end, minutes):
    start, end = datetime.fromisoformat(start), datetime.fromisoformat(end)
    blocks = build_schedule_blocks([target("M31", start, end)], timezone_name="America/New_York")
    assert sum(b["duration_minutes"] for b in blocks) == minutes
    assert _darkness_minutes({"astronomical_darkness_start": start.isoformat(),
                              "astronomical_darkness_end": end.isoformat()}, "America/New_York") == minutes


def test_visibility_stops_before_below_floor_sample():
    with patch("app.services.planner_service.get_altitudes_at", return_value=[30, 25, 21, 19, 10]):
        visibility = get_dark_visibility("M31", START, START + timedelta(hours=1))
    assert visibility["recommended_end_datetime"] == START + timedelta(minutes=30)


def test_hosted_endpoint_keeps_later_rising_targets_outside_shortlist():
    names = ["M27", "M57", "M81", "M42", "M13", "M51", "M63", "M64"]
    def visibility(object_name, **kwargs):
        index = names.index(object_name)
        return {"known_position": True, "usable_dark_minutes": 60,
                "usable_dark_hours": 1, "maximum_dark_altitude": 70-index,
                "average_dark_altitude": 70-index,
                "recommended_start_datetime": START + timedelta(hours=index),
                "recommended_end_datetime": START + timedelta(hours=index+1),
                "target_geometry": None}
    with workflow() as flow, patch("app.services.planner_service.TARGETS", names), \
            patch("app.services.planner_service.get_dark_visibility", visibility), TestClient(flow.app) as client:
        plan = flow.plan(client)
    assert {b["object"] for b in plan["schedule"]["blocks"]} == set(names)
    assert plan["schedule"]["unscheduled_dark_minutes"] == 0
    assert plan["schedule"]["blocks"][-1]["end"] == "2025-01-16 04:00 AM"


def test_returning_target_keeps_one_exact_integration_budget():
    selected = target("M27", START, END, exposure=15, remaining_seconds=3020, additional_subframes=202)
    selected["schedule_windows"] = [
        {"start": START.isoformat(), "end": (START + timedelta(minutes=30)).isoformat()},
        {"start": (START + timedelta(hours=2)).isoformat(), "end": (START + timedelta(hours=3)).isoformat()},
    ]
    blocks = build_schedule_blocks([selected], timezone_name="UTC")
    assert [b["planned_subframes"] for b in blocks] == [100, 101]
    assert sum(b["imaging_minutes"] * 60 for b in blocks) == 3015
    assert all(b["duration_minutes"] >= 30 for b in blocks)


def test_split_run_durations_equal_actual_elapsed_time():
    end = START + timedelta(hours=7)
    selected = target("M27", START, end, exposure=10)
    result = build_tonight_schedule({"decision": "Proceed", "notes": [], "weather": {}, "moon": {},
        "recommended_target": selected, "alternatives": [], "darkness": {
            "astronomical_darkness_start": START.isoformat(), "astronomical_darkness_end": end.isoformat()}}, "UTC")
    assert result["allocated_minutes"] == 420
    assert result["unscheduled_dark_minutes"] == 0
    assert result["gaps"] == []
    for block in result["blocks"]:
        elapsed = (datetime.fromisoformat(block["end_at"]) - datetime.fromisoformat(block["start_at"])).total_seconds()
        assert block["duration_minutes"] * 60 == pytest.approx(elapsed)
        assert block["imaging_minutes"] * 60 == pytest.approx(block["planned_subframes"] * 10)


def test_too_little_goal_for_whole_frames_does_not_create_short_block():
    blocks = build_schedule_blocks([target("M27", START, END, exposure=120, remaining_seconds=1510)])
    assert blocks == []  # 24 minutes of whole frames + five setup is below minimum.


def test_dst_visibility_samples_cover_every_real_quarter_hour():
    from zoneinfo import ZoneInfo
    from app.services.planner_service import generate_sample_times
    start = datetime(2026, 11, 1, 0, tzinfo=ZoneInfo("America/New_York"))
    end = start.replace(hour=4)
    samples = generate_sample_times(start, end)
    assert len(samples) == 21
    assert all((b.astimezone(timezone.utc) - a.astimezone(timezone.utc)).total_seconds() == 900
               for a, b in zip(samples, samples[1:]))


def test_visibility_interval_crossing_fall_fold_remains_schedulable():
    from zoneinfo import ZoneInfo
    start = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"))
    end = start.replace(minute=15, fold=1)
    with patch("app.services.planner_service.get_altitudes_at", return_value=[40, 40, 40, 40]):
        visibility = get_dark_visibility("M27", start, end)
    assert visibility["usable_dark_minutes"] == 45
    selected = target("M27", start, end)
    selected["schedule_windows"] = visibility["schedule_windows"]
    blocks = build_schedule_blocks([selected], timezone_name="America/New_York")
    assert sum(block["duration_minutes"] for block in blocks) == 45


def test_explicit_empty_target_selection_stays_empty():
    from app.services.planner_service import get_tonight_plan
    with workflow(), patch("app.services.planner_service.build_target_plan") as build:
        plan = get_tonight_plan(None, target_names=[], use_capture_history=False)
    build.assert_not_called()
    assert plan["schedule_candidates"] == []


def test_known_rig_rejects_target_that_cannot_fit_single_frame():
    from app.core.planning_context import ObservatoryContext
    from app.services.planner_service import get_tonight_plan
    context = ObservatoryContext("test", 0, 0, "UTC", rig_profile_key="dwarf-mini")
    with workflow(), patch("app.services.planner_service.build_target_plan") as build:
        plan = get_tonight_plan(None, context, target_names=["M31"], use_capture_history=False)
    build.assert_not_called()
    assert plan["schedule_candidates"] == []
    assert any("single-frame" in note for note in plan["notes"])


@pytest.mark.parametrize("latitude,month", [(89, 6), (-89, 12), (89, 12)])
def test_polar_unbounded_darkness_returns_no_fabricated_interval(latitude, month):
    from astropy.utils import iers
    from app.core.planning_context import ObservatoryContext
    from app.services.astronomy_service import get_darkness_info
    context = ObservatoryContext("polar", latitude, 0, "UTC")
    with iers.conf.set_temp("auto_download", False):
        info = get_darkness_info(datetime(2026, month, 21, 12, tzinfo=timezone.utc), context)
    assert info["astronomical_darkness_start"] is None
    assert info["astronomical_darkness_end"] is None


def test_hosted_no_darkness_response_is_explicit():
    darkness = {"sunset": None, "astronomical_darkness_start": None, "astronomical_darkness_end": None}
    with workflow() as flow, patch("app.services.planner_service.get_darkness_info", return_value=darkness), \
            patch("app.services.planner_service.get_darkness_window_datetimes", return_value=(None, None, None)), \
            TestClient(flow.app) as client:
        plan = flow.plan(client)
    assert plan["schedule"]["blocks"] == []
    assert "bounded" in plan["message"]
