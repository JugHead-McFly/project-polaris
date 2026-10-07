"""Synthetic obstruction geometry only; no account data or live services."""
from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.core.obstruction_profile import ObstructionProfile
from app.core.planning_context import ObservatoryContext
from app.services import planner_service as planner
from app.services.astronomy_service import get_horizontal_positions_at
from app.services.obstruction_service import (
    evaluate_profile_visibility, interval_exclusion_reason, profile_sample_times,
)
from app.services.scheduler_service import build_schedule_blocks, _parse_schedule_time


def profile(**overrides):
    return ObstructionProfile.model_validate({
        "complete_coverage": True,
        "horizon": [{"azimuth_degrees": 0, "altitude_degrees": 0},
                    {"azimuth_degrees": 180, "altitude_degrees": 0}],
        **overrides,
    })


def sector(start=350, end=10, low=60, high=90):
    return {"start_azimuth_degrees": start, "end_azimuth_degrees": end,
            "minimum_altitude_degrees": low, "maximum_altitude_degrees": high}


def context(obstruction=None, timezone="America/Phoenix"):
    return ObservatoryContext(name="Synthetic site", latitude=33, longitude=-112,
                              timezone_name=timezone, obstruction_profile=obstruction)


def at(hour=21, minute=0, timezone="America/Phoenix"):
    return datetime(2026, 8, 23, hour, minute, tzinfo=ZoneInfo(timezone))


def test_cyclic_interpolation_and_exact_knots():
    survey = profile(horizon=[{"azimuth_degrees": 10, "altitude_degrees": 40},
                              {"azimuth_degrees": 350, "altitude_degrees": 20}])
    assert survey.horizon_altitude(0) == survey.horizon_altitude(360) == 30
    assert survey.horizon_altitude(355) == 25
    assert survey.horizon_altitude(10) == 40
    assert survey.horizon_altitude(180) == 30


@pytest.mark.parametrize("overrides", [
    {"complete_coverage": False}, {"complete_coverage": 1},
    {"complete_coverage": "true"}, {"unknown": 1},
    {"clearance_degrees": -1}, {"clearance_degrees": 11},
    {"clearance_degrees": float("nan")}, {"clearance_degrees": True},
    {"horizon": []},
    {"horizon": [{"azimuth_degrees": 0, "altitude_degrees": 1}] * 2},
    {"horizon": [{"azimuth_degrees": 180, "altitude_degrees": 1},
                 {"azimuth_degrees": 0, "altitude_degrees": 1}]},
    *[{"horizon": [{"azimuth_degrees": az, "altitude_degrees": alt},
                   {"azimuth_degrees": 180, "altitude_degrees": 0}]}
      for az, alt in [(360, 10), (-1, 10), (0, -1), (0, 91), (True, 0),
                      (0, float("inf")), (float("nan"), 10), ("0", 0)]],
    {"sectors": [sector(start=10, end=10)]},
    {"sectors": [sector(low=80, high=60)]},
    {"sectors": [sector(low=60, high=60)]},
    {"sectors": [sector(start=360)]},
])
def test_invalid_profiles_rejected(overrides):
    with pytest.raises(ValidationError):
        profile(**overrides)


def test_coverage_assertion_required_and_profile_immutable():
    with pytest.raises(ValidationError):
        ObstructionProfile.model_validate({"horizon": profile().model_dump()["horizon"]})
    survey = profile()
    with pytest.raises(ValidationError):
        survey.horizon[0].altitude_degrees = 90
    with pytest.raises(TypeError):
        context({"complete_coverage": True})


@pytest.mark.parametrize("az,alt,blocked", [
    (0, 50, False), (0, 59, True), (0, 90, True),
    (350, 70, True), (10, 70, True), (11, 70, False), (349, 70, False),
    (180, 20, False), (180, 19.999, True),
])
def test_roof_wrap_boundaries_and_independent_quality_floor(az, alt, blocked):
    reason = interval_exclusion_reason(profile(sectors=[sector()]), (az, alt), (az, alt), 20)
    assert bool(reason) is blocked


def test_clearance_equality_is_blocked_and_lower_horizon_cannot_lower_floor():
    survey = profile(horizon=[{"azimuth_degrees": 0, "altitude_degrees": 25},
                              {"azimuth_degrees": 180, "altitude_degrees": 25}])
    assert "horizon" in interval_exclusion_reason(survey, (10, 26), (10, 26), 20)
    assert interval_exclusion_reason(survey, (10, 26.001), (10, 26.001), 20) is None
    assert interval_exclusion_reason(profile(clearance_degrees=0), (0, 19), (0, 19), 20)


def test_swept_arc_catches_thin_roof_and_horizon_peak_between_clear_samples():
    roof = profile(sectors=[sector(start=0.1, end=0.2, low=30)])
    assert interval_exclusion_reason(roof, (359, 40), (1, 40), 20)
    assert interval_exclusion_reason(roof, (1, 40), (359, 40), 20)
    horizon = profile(horizon=[{"azimuth_degrees": 0, "altitude_degrees": 50},
                               {"azimuth_degrees": 1, "altitude_degrees": 0},
                               {"azimuth_degrees": 359, "altitude_degrees": 0}])
    assert "horizon" in interval_exclusion_reason(horizon, (359, 40), (1, 40), 20)
    assert "quickly" in interval_exclusion_reason(profile(), (0, 80), (6, 80), 20)


@pytest.mark.parametrize("position", [None, (0, float("nan")), (360, 40), (0, 91)])
def test_unknown_or_invalid_positions_fail_closed(position):
    assert interval_exclusion_reason(profile(), position, (0, 40), 20) == "Position unavailable"


def visibility(survey, positions, start=None):
    start = start or at()
    with patch.object(planner, "get_horizontal_positions_at", return_value=positions):
        return planner.get_dark_visibility("M31", start, start + timedelta(minutes=len(positions)-1),
                                           observatory=context(survey, str(start.tzinfo)))


def test_blocked_middle_yields_separate_windows_and_schedule_stays_in_longest():
    survey = profile(sectors=[sector(start=90, end=100, low=20)])
    # Enter and leave the sector gradually; longest window is after the blockage.
    positions = [(80, 40)] * 61 + [(85, 40), (90, 40), (95, 40), (100, 40), (105, 40)] + [(110, 40)] * 91
    result = visibility(survey, positions)
    assert len(result["obstruction_windows"]) == 2
    assert result["recommended_start_datetime"] == at() + timedelta(minutes=65)
    assert result["recommended_end_datetime"] == at() + timedelta(minutes=156)
    assert result["usable_dark_minutes"] == 91
    assert "sector" in result["obstruction_explanation"]
    candidate = {"observable": True, "planner_score": 100,
                 "advisor": {"object": "M31", "recommended_sub_exposure_seconds": 10},
                 "recommended_start": result["recommended_start_datetime"].strftime("%Y-%m-%d %I:%M %p"),
                 "recommended_end": result["recommended_end_datetime"].strftime("%Y-%m-%d %I:%M %p")}
    blocks = build_schedule_blocks([candidate])
    assert blocks
    for block in blocks:
        begin = _parse_schedule_time(block["start"])
        end = _parse_schedule_time(block["end"])
        assert result["recommended_start_datetime"] <= begin < end <= result["recommended_end_datetime"]
        for index, position in enumerate(positions):
            if begin <= at() + timedelta(minutes=index) <= end:
                assert interval_exclusion_reason(survey, position, position, 20) is None


def test_does_not_extend_last_clear_sample_into_blockage():
    result = visibility(profile(), [(0, 40)] * 51 + [(0, 10)] * 20)
    assert result["usable_dark_minutes"] == 50
    assert result["recommended_end_datetime"] == at() + timedelta(minutes=50)


def test_no_profile_exact_legacy_parity_and_no_direction_calls():
    with patch.object(planner, "get_altitudes_at", return_value=[30, 40, 10]), patch.object(
        planner, "get_horizontal_positions_at", side_effect=AssertionError("legacy path changed")
    ):
        implicit = planner.get_dark_visibility("M31", at(), at() + timedelta(minutes=30))
        explicit = planner.get_dark_visibility("M31", at(), at() + timedelta(minutes=30), observatory=context())
    assert implicit == explicit
    assert implicit["usable_dark_minutes"] == 30  # preserve the pre-existing endpoint policy
    assert "obstruction_explanation" not in implicit


def test_request_contexts_cannot_leak_profile_across_accounts_or_sites():
    alice = context(profile(horizon=[{"azimuth_degrees": 0, "altitude_degrees": 90},
                                     {"azimuth_degrees": 180, "altitude_degrees": 90}]))
    bob = replace(context(profile()), name="Bob other site", longitude=151)
    with patch.object(planner, "get_horizontal_positions_at", return_value=[(0, 40)] * 61):
        first = planner.get_dark_visibility("M31", at(), at(22), observatory=alice)
        second = planner.get_dark_visibility("M31", at(), at(22), observatory=bob)
        repeated = planner.get_dark_visibility("M31", at(), at(22), observatory=alice)
    assert first == repeated
    assert first["usable_dark_minutes"] == 0
    assert second["usable_dark_minutes"] == 60
    assert context().obstruction_profile is None


def test_rounding_midnight_timezone_and_no_extension_past_end():
    start = at(23, 59, "America/New_York").replace(second=20)
    times = profile_sample_times(start, start + timedelta(minutes=61))
    assert times[0].isoformat() == "2026-08-24T00:00:00-04:00"
    assert times[-1].isoformat() == "2026-08-24T01:00:00-04:00"
    assert all(start <= time <= start + timedelta(minutes=61) for time in times)
    result = visibility(profile(), [(0, 40)] * 61, at(23, 30, "America/New_York"))
    assert result["target_geometry"]["samples"][-1]["label"] == "12:30 AM next day"


def test_dst_transition_fails_closed_without_changing_legacy_schedule_format():
    start = datetime(2026, 11, 1, 0, 30, tzinfo=ZoneInfo("America/New_York"))
    end = datetime(2026, 11, 1, 2, 30, tzinfo=start.tzinfo)
    times = profile_sample_times(start, end)
    windows, reasons = evaluate_profile_visibility(profile(), times, [(0, 40)] * len(times), 20)
    assert not windows
    assert "Timezone offset transition" in reasons[0]


def test_missing_samples_and_short_window():
    with pytest.raises(ValueError):
        evaluate_profile_visibility(profile(), [at(), at(22)], [], 20)
    with pytest.raises(ValueError):
        profile_sample_times(datetime(2026, 1, 1), at())
    assert evaluate_profile_visibility(profile(), [], [], 20)[0] == []
    result = visibility(profile(), [None] * 61)
    assert result["known_position"] is False
    assert result["recommended_start_datetime"] is None
    assert "Position unavailable" in result["obstruction_explanation"]


def test_real_horizontal_conversion_preserves_site_and_absolute_time():
    from astropy.utils import iers
    with iers.conf.set_temp("auto_download", False):
        local = get_horizontal_positions_at("M31", [at()], context())[0]
        utc = get_horizontal_positions_at("M31", [at().astimezone(ZoneInfo("UTC"))], context())[0]
        other = get_horizontal_positions_at("M31", [at()], replace(context(), longitude=151))[0]
    assert local == pytest.approx(utc)
    assert local != pytest.approx(other)
    assert 0 <= local[0] < 360 and -90 <= local[1] <= 90
    assert get_horizontal_positions_at("UNRESOLVED", [at()], context()) == [None]


@pytest.mark.parametrize("blocked", [False, True])
def test_target_plan_explains_profile_and_scheduler_uses_result(blocked):
    survey = profile(sectors=[sector(start=350, end=10, low=20)] if blocked else [])
    with (patch.object(planner, "get_horizontal_positions_at", return_value=[(0, 40)] * 61),
          patch.object(planner, "get_altitude_at", return_value=40),
          patch.object(planner, "get_moon_separation_at", return_value=90),
          patch.object(planner, "get_moon_warning_at", return_value=None),
          patch.object(planner, "get_transit_time", return_value=None)):
        result = planner.build_target_plan(object(), "M31", at(), at(22),
                                           observatory=context(survey), use_capture_history=False)
    assert result["observable"] is not blocked
    assert "User-supplied obstruction profile" in result["selection_reason"]
    assert "full image frame" in result["selection_reason"]
    blocks = build_schedule_blocks([result])
    assert bool(blocks) is not blocked
    if blocked:
        assert "Overhead/sector obstruction" in result["selection_reason"]
        assert result["recommended_start"] is None
        assert result["recommended_end"] is None


def test_short_clear_islands_cannot_combine_to_meet_planning_minimum():
    positions = [(0, 40)] * 31 + [None] + [(0, 40)] * 31
    result = visibility(profile(), positions)
    assert result["usable_dark_minutes"] == 30
    assert len(result["obstruction_windows"]) == 2
    assert "45-minute" in result["obstruction_explanation"]


@pytest.mark.parametrize("times", [[at(), at(22)], [at(), at()], [at(22), at()]])
def test_sparse_or_unordered_samples_cannot_bridge_unknown_intervals(times):
    with pytest.raises(ValueError):
        evaluate_profile_visibility(profile(), times, [(0, 40)] * len(times), 20)


@pytest.mark.parametrize("fold", [0, 1])
def test_window_wholly_inside_repeated_hour_fails_closed(fold):
    # No offset transition inside this window: the old transition check missed it.
    start = datetime(2026, 11, 1, 1, 5, fold=fold, tzinfo=ZoneInfo("America/New_York"))
    end = datetime(2026, 11, 1, 1, 55, fold=fold, tzinfo=start.tzinfo)
    with (patch.object(planner, "get_horizontal_positions_at", return_value=[(0, 40)] * 51),
          patch.object(planner, "get_altitude_at", return_value=40),
          patch.object(planner, "get_moon_separation_at", return_value=90),
          patch.object(planner, "get_moon_warning_at", return_value=None),
          patch.object(planner, "get_transit_time", return_value=None)):
        result = planner.build_target_plan(object(), "M31", start, end,
                    observatory=context(profile(), "America/New_York"), use_capture_history=False)
    assert result["observable"] is False
    assert result["recommended_start"] is None
    assert "Ambiguous local time" in result["selection_reason"]
    assert build_schedule_blocks([result], timezone_name="America/New_York") == []


def test_profile_normalizes_utc_bounds_to_site_before_schedule_serialization():
    start = at().astimezone(ZoneInfo("UTC"))
    end = at(22).astimezone(ZoneInfo("UTC"))
    with (patch.object(planner, "get_horizontal_positions_at", return_value=[(0, 40)] * 61),
          patch.object(planner, "get_altitude_at", return_value=40),
          patch.object(planner, "get_moon_separation_at", return_value=90),
          patch.object(planner, "get_moon_warning_at", return_value=None),
          patch.object(planner, "get_transit_time", return_value=None)):
        result = planner.build_target_plan(object(), "M31", start, end,
                                           observatory=context(profile()), use_capture_history=False)
    assert result["recommended_start"] == "2026-08-23 09:00 PM"
    assert result["recommended_end"] == "2026-08-23 10:00 PM"
    blocks = build_schedule_blocks([result], timezone_name="America/Phoenix")
    assert blocks
    for block in blocks:
        assert start <= _parse_schedule_time(block["start"]) < _parse_schedule_time(block["end"]) <= end


def test_profile_rejects_naive_bounds_before_site_conversion():
    with patch.object(planner, "get_horizontal_positions_at") as positions:
        with pytest.raises(ValueError, match="timezone-aware"):
            planner.get_dark_visibility("M31", at().replace(tzinfo=None), at(22),
                                         observatory=context(profile()))
    positions.assert_not_called()
