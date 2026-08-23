from app.services.dew_risk_service import assess_dew_risk


START = "2026-08-23 09:00 PM"
END = "2026-08-24 01:00 AM"


def _weather(*points):
    return {
        "hourly_forecast": {
            time: {
                "temperature_f": temperature,
                "dew_point_f": dew_point,
            }
            for time, temperature, dew_point in points
        }
    }


def test_low_dew_risk_uses_smallest_spread_in_planned_window():
    result = assess_dew_risk(
        _weather(
            ("2026-08-23T21:00", 70, 58),
            ("2026-08-23T23:00", 65, 57),
            ("2026-08-24T02:00", 59, 58),
        ),
        planned_start=START,
        planned_end=END,
    )

    assert result["level"] == "low"
    assert result["spread_f"] == 8.0
    assert result["forecast_at"] == "2026-08-23 11:00 PM"
    assert result["action"].startswith("No special dew action")


def test_watch_dew_risk_recommends_preparation_and_monitoring():
    result = assess_dew_risk(
        _weather(("2026-08-23T22:00", 64, 59)),
        planned_start=START,
        planned_end=END,
    )

    assert result["level"] == "watch"
    assert result["label"] == "Watch for dew"
    assert "Have dew control ready" in result["action"]
    assert "condensation" in result["action"]


def test_high_dew_risk_recommends_dew_control_from_start():
    result = assess_dew_risk(
        _weather(("2026-08-23T22:00", 61, 59)),
        planned_start=START,
        planned_end=END,
    )

    assert result["level"] == "high"
    assert result["label"] == "High dew risk"
    assert "Use dew control from the start" in result["action"]


def test_dew_risk_is_unavailable_without_complete_planned_data():
    result = assess_dew_risk(
        _weather(("2026-08-23T22:00", 61, None)),
        planned_start=START,
        planned_end=END,
    )

    assert result == {
        "level": "unavailable",
        "label": "Dew risk unavailable",
        "summary": "Planned-window temperature or dew-point data is incomplete.",
        "action": (
            "Check local conditions before imaging and keep dew control "
            "available if moisture begins forming."
        ),
        "temperature_f": None,
        "dew_point_f": None,
        "spread_f": None,
        "forecast_at": None,
    }


def test_dew_risk_is_unavailable_when_window_is_only_partially_complete():
    result = assess_dew_risk(
        _weather(
            ("2026-08-23T21:00", 70, 58),
            ("2026-08-23T22:00", 67, None),
        ),
        planned_start=START,
        planned_end=END,
    )

    assert result["level"] == "unavailable"
    assert result["spread_f"] is None


def test_dew_point_above_temperature_is_reported_as_zero_gap():
    result = assess_dew_risk(
        _weather(("2026-08-23T22:00", 59, 61)),
        planned_start=START,
        planned_end=END,
    )

    assert result["level"] == "high"
    assert result["spread_f"] == 0.0
    assert "0°F" in result["summary"]


def test_dew_risk_boundaries_are_conservative():
    high = assess_dew_risk(
        _weather(("2026-08-23T22:00", 63, 60)),
        planned_start=START,
        planned_end=END,
    )
    watch = assess_dew_risk(
        _weather(("2026-08-23T22:00", 67, 60)),
        planned_start=START,
        planned_end=END,
    )
    low = assess_dew_risk(
        _weather(("2026-08-23T22:00", 67.1, 60)),
        planned_start=START,
        planned_end=END,
    )

    assert high["level"] == "high"
    assert watch["level"] == "watch"
    assert low["level"] == "low"


def test_planned_start_values_are_used_when_hourly_window_is_missing():
    result = assess_dew_risk(
        {
            "planned_temperature_f": 58,
            "planned_dew_point_f": 56,
            "planned_temperature_at": "2026-08-23 09:00 PM",
        },
        planned_start=START,
        planned_end=END,
    )

    assert result["level"] == "high"
    assert result["forecast_at"] == "2026-08-23 09:00 PM"
