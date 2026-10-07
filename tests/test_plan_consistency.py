from app.api.tonight import _build_operator_message
from app.services.planner_service import get_weather_decision
from app.services.scheduler_service import _plan_end_reason
from app.api.tonight import _build_legacy_target


def test_hosted_target_uses_synced_session_count_and_unknown_quality():
    plan = dict.fromkeys([
        "observable", "current_altitude", "transit_time", "moon_warning",
        "recommended_start", "recommended_end", "moon_separation_degrees",
        "selection_reason",
    ])
    plan["advisor"] = {"object": "M27", "current_integration_hours": 3.11,
                       "current_integration_seconds": 11196}
    target = _build_legacy_target(
        None, plan, use_capture_history=False,
        capture_progress={"M27": {"sessions": 2}},
    )
    assert target["session_count"] == 2
    assert target["best_quality"] is None
    assert target["total_integration_seconds"] == 11196


def test_stale_high_rated_forecast_explains_caution():
    weather = {"observing_rating": 5, "cache_status": "stale"}
    decision = get_weather_decision(weather)
    assert decision == "Use Caution"
    message = _build_operator_message({"decision": decision, "weather": weather})
    assert "older forecast" in message
    assert "5/5" not in message
    assert get_weather_decision({"observing_rating": 5, "cache_status": "fresh"}) == "Proceed"


def test_allocated_goal_explains_early_plan_end():
    blocks = [{"object": "M27", "imaging_minutes": 114}, {"object": "NGC6633", "imaging_minutes": 75}]
    targets = [{"advisor": {"object": "NGC6633", "remaining_seconds": 4500}}]
    assert "integration goal is allocated" in _plan_end_reason(blocks, targets)
    assert "not a weather cutoff" in _plan_end_reason(blocks, targets)
    targets[0]["advisor"]["remaining_seconds"] = 9000
    assert "End of selected plan" in _plan_end_reason(blocks, targets)
    assert _plan_end_reason([], targets) is None
