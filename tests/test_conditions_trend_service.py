from app.services.conditions_trend_service import assess_conditions_trend


START = "2026-08-23 09:00 PM"
END = "2026-08-23 11:00 PM"


def _weather(*points):
    return {
        "hourly_forecast": {
            time: {
                "cloud_cover_percent": cloud,
                "humidity_percent": humidity,
                "wind_speed_mph": wind,
            }
            for time, cloud, humidity, wind in points
        }
    }


def test_conditions_trend_reports_improving_and_explains_main_driver():
    result = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 60, 70, 8),
            ("2026-08-23T23:00", 30, 70, 8),
        ),
        planned_start=START,
        planned_end=END,
    )

    assert result["direction"] == "improving"
    assert result["label"] == "Improving"
    assert result["message"].startswith("Improving: later may be better.")
    assert result["basis"] == "Cloud cover drops from 60% to 30%."


def test_conditions_trend_reports_steady_without_noise_details():
    result = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 20, 60, 7),
            ("2026-08-23T23:00", 25, 62, 7.5),
        ),
        planned_start=START,
        planned_end=END,
    )

    assert result["direction"] == "steady"
    assert result["message"] == "Steady: start when the window opens."
    assert result["basis"] is None


def test_conditions_trend_reports_worsening_and_favors_window_opening():
    result = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 10, 55, 5),
            ("2026-08-23T23:00", 40, 55, 5),
        ),
        planned_start=START,
        planned_end=END,
    )

    assert result["direction"] == "worsening"
    assert "favor the window opening" in result["message"]
    assert result["basis"] == "Cloud cover rises from 10% to 40%."


def test_conditions_trend_is_unavailable_with_missing_or_invalid_data():
    missing = assess_conditions_trend(
        _weather(("2026-08-23T21:00", 20, 60, None)),
        planned_start=START,
        planned_end=END,
    )
    invalid_window = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 20, 60, 5),
            ("2026-08-23T23:00", 10, 60, 5),
        ),
        planned_start="not a date",
        planned_end=END,
    )

    assert missing["direction"] == "unavailable"
    assert invalid_window["direction"] == "unavailable"
    assert "check live conditions" in missing["message"]


def test_conditions_trend_is_unavailable_when_window_is_partially_complete():
    result = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 40, 60, 5),
            ("2026-08-23T22:00", 30, 60, None),
            ("2026-08-23T23:00", 20, 60, 5),
        ),
        planned_start=START,
        planned_end=END,
    )

    assert result["direction"] == "unavailable"


def test_conditions_trend_requires_at_least_one_hour_of_forecast_span():
    result = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 40, 60, 5),
            ("2026-08-23T21:30", 10, 60, 5),
        ),
        planned_start=START,
        planned_end=END,
    )

    assert result["direction"] == "unavailable"


def test_conditions_trend_requires_forecast_coverage_near_window_boundaries():
    result = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 40, 60, 5),
            ("2026-08-23T22:00", 20, 60, 5),
        ),
        planned_start=START,
        planned_end="2026-08-24 01:00 AM",
    )

    assert result["direction"] == "unavailable"


def test_conditions_trend_boundaries_are_inclusive():
    improving = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 30, 60, 5),
            ("2026-08-23T22:00", 20, 60, 5),
        ),
        planned_start=START,
        planned_end=END,
    )
    worsening = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 20, 60, 5),
            ("2026-08-23T22:00", 30, 60, 5),
        ),
        planned_start=START,
        planned_end=END,
    )
    steady = assess_conditions_trend(
        _weather(
            ("2026-08-23T21:00", 20, 60, 5),
            ("2026-08-23T22:00", 29.9, 60, 5),
        ),
        planned_start=START,
        planned_end=END,
    )

    assert improving["direction"] == "improving"
    assert worsening["direction"] == "worsening"
    assert steady["direction"] == "steady"
