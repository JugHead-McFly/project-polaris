"""Selected-instant facts are not nightly suitability or landscape clearance."""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.api.sky_view import SkyViewRequest, calculate_view
from app.core.planning_context import ObservatoryContext
from app.data.targets import TARGETS
from app.services import planner_service as planner
from app.services.astronomy_service import get_altitude_at, get_sun_altitude_at, _get_observer, to_astropy_time


def request(at="2026-10-08T04:00:00Z", latitude=33, longitude=-112):
    return SkyViewRequest.model_validate({
        "at": at,
        "location": {"latitude": latitude, "longitude": longitude,
                     "timezone_name": "America/Phoenix"},
        "targets": ["M31", "M57", "JUPITER"],
    })


@pytest.mark.parametrize("sun,state", [(-18, "astronomical_darkness"),
    (-18.001, "astronomical_darkness"), (-17.999, "not_astronomical_darkness"),
    (10, "not_astronomical_darkness"), (float("nan"), "unavailable")])
def test_selected_instant_floor_and_darkness_boundaries(sun, state):
    with (patch("app.api.sky_view.get_sun_altitude_at", return_value=sun),
          patch("app.api.sky_view.get_horizontal_positions_at",
                side_effect=[[(0, 19.999)], [(0, 20)], [None]])):
        result = calculate_view(request())
    assert result["selected_time_conditions"]["darkness_state"] == state
    assert result["selected_time_conditions"]["weather_state"] == "not_evaluated"
    assert [row["imaging_altitude_state"] for row in result["targets"]] == [
        "below_minimum", "at_or_above_minimum", "unavailable"]
    assert result["applied_to_tonight"] is False


def test_solar_failure_leaves_target_coordinates_available_without_darkness_claim():
    with patch("app.api.sky_view.get_sun_altitude_at", side_effect=ValueError("Unavailable")):
        result = calculate_view(request())
    assert result["selected_time_conditions"]["darkness_state"] == "unavailable"
    assert result["selected_time_conditions"]["sun_altitude_degrees"] is None
    assert all(row["status"] != "unavailable" for row in result["targets"])


@pytest.mark.parametrize("latitude,longitude,at", [
    (33, -112, "2026-10-08T04:00:00Z"), (-33, 151, "2026-10-08T08:00:00Z")])
def test_inspector_agrees_with_existing_fixed_planet_and_solar_calculations(latitude, longitude, at):
    payload = request(at, latitude, longitude)
    context = ObservatoryContext(name="Synthetic", **payload.location.model_dump())
    result = calculate_view(payload)
    for row in result["targets"]:
        assert round(row["altitude_degrees"], 1) == get_altitude_at(row["id"], payload.at, context)
    # This is the existing nightly darkness method, at the exact selected instant.
    expected = float(_get_observer(context).sun_altaz(to_astropy_time(payload.at, context)).alt.deg)
    assert get_sun_altitude_at(payload.at, context) == pytest.approx(expected)
    assert result["selected_time_conditions"]["sun_altitude_degrees"] == pytest.approx(expected)


def test_catalog_candidates_are_evaluated_before_observability_shortlist():
    # High-scoring blocked plans must not crowd a late low-scoring usable target
    # out of the evaluation pool. There is deliberately no ranking rewrite.
    visited = []
    winner = sorted(TARGETS)[-1]
    start = datetime(2026, 10, 8, tzinfo=timezone.utc)

    def build(**kwargs):
        name = kwargs["object_name"]
        visited.append(name)
        return {"advisor": {"object": name}, "observable": name == winner,
                "planner_score": 1 if name == winner else 100,
                "maximum_dark_altitude": 40, "recommended_start": "2026-10-08 12:00 AM"}

    with ExitStack() as stack:
        for name, value in [("get_weather_summary", {"observing_rating": 5}),
                            ("get_moon_info", {}), ("get_darkness_info", {}),
                            ("get_darkness_window_datetimes", (start, start, start + timedelta(hours=6)))]:
            stack.enter_context(patch.object(planner, name, return_value=value))
        stack.enter_context(patch.object(planner, "build_target_plan", side_effect=build))
        stack.enter_context(patch.object(planner, "apply_tonight_settings", side_effect=lambda **kw: kw["advisor"]))
        stack.enter_context(patch("app.services.cloud_forecast_service.summarize_dark_window", return_value={}))
        result = planner.get_tonight_plan(object(), use_capture_history=False)
    assert len(visited) == len(TARGETS)
    assert set(visited) == set(TARGETS)
    assert result["recommended_target"]["advisor"]["object"] == winner
    assert result["alternatives"] == []
