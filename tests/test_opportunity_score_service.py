from app.services.opportunity_score_service import calculate_opportunity_score
from app.services.opportunity_score_service import explain_opportunity_for_decision


def component(payload, key):
    return next(item for item in payload["components"] if item["key"] == key)


def score(*, weather=None, moon=None, darkness=None, target=None):
    return calculate_opportunity_score(
        weather=weather or {},
        moon=moon or {},
        darkness=darkness or {},
        target=target,
    )


def test_cloud_and_stability_uses_continuous_subweights():
    perfect = score(weather={
        "cloud_cover_percent": 0,
        "humidity_percent": 50,
        "wind_speed_mph": 5,
    })
    midpoint = score(weather={
        "cloud_cover_percent": 50,
        "humidity_percent": 75,
        "wind_speed_mph": 12.5,
    })
    worst = score(weather={
        "cloud_cover_percent": 100,
        "humidity_percent": 100,
        "wind_speed_mph": 20,
    })

    assert component(perfect, "cloud")["points"] == 45
    assert component(midpoint, "cloud")["points"] == 22.5
    assert component(worst, "cloud")["points"] == 0


def test_darkness_scales_to_full_credit_at_eight_hours():
    four_hours = score(darkness={
        "astronomical_darkness_start": "2026-07-17 10:00 PM",
        "astronomical_darkness_end": "2026-07-18 02:00 AM",
    })
    eight_hours = score(darkness={
        "astronomical_darkness_start": "2026-07-17 08:00 PM",
        "astronomical_darkness_end": "2026-07-18 04:00 AM",
    })

    assert component(four_hours, "night")["points"] == 10
    assert component(eight_hours, "night")["points"] == 20
    assert "10:00 PM to 2:00 AM" in component(four_hours, "night")["detail"]


def test_moon_illumination_maps_linearly_to_fifteen_points():
    expected = {0: 15, 50: 7.5, 75: 3.8, 100: 0}
    for illumination, points in expected.items():
        payload = score(moon={"illumination_percent": illumination})
        assert component(payload, "moon")["points"] == points


def test_moon_detail_preserves_phase_and_horizon_context():
    payload = score(moon={
        "illumination_percent": 75,
        "phase_name": "Waxing Gibbous",
        "above_horizon": False,
        "next_moonrise": "2026-08-22 03:52 PM",
    })

    assert component(payload, "moon")["detail"] == (
        "Waxing Gibbous · 75% illuminated. "
        "Below the horizon now; rises 3:52 PM."
    )


def test_target_altitude_scales_between_twenty_degrees_and_zenith():
    expected = {20: 0, 55: 2.5, 90: 5}
    for altitude, points in expected.items():
        payload = score(target={"maximum_dark_altitude": altitude})
        assert component(payload, "altitude")["points"] == points


def test_transparency_and_seeing_scale_from_7timer_bins():
    transparency_points = [10, 8.6, 7.1, 5.7, 4.3, 2.9, 1.4, 0]
    seeing_points = [5, 4.3, 3.6, 2.9, 2.1, 1.4, 0.7, 0]

    for index in range(1, 9):
        payload = score(weather={
            "planned_transparency_index": index,
            "planned_transparency_forecast_at": "2026-07-17 09:00 PM",
            "planned_seeing_index": index,
            "planned_seeing_forecast_at": "2026-07-17 09:00 PM",
        })

        visibility = component(payload, "visibility")
        seeing = component(payload, "seeing")
        assert visibility["points"] == transparency_points[index - 1]
        assert visibility["source"] == "Forecast"
        assert seeing["points"] == seeing_points[index - 1]
        assert seeing["source"] == "Forecast"
        assert "near 9:00 PM" in visibility["description"]
        assert "near 9:00 PM" in seeing["description"]


def test_astro_scores_do_not_reuse_cloud_humidity_or_wind():
    clear = score(weather={
        "cloud_cover_percent": 0,
        "humidity_percent": 40,
        "wind_speed_mph": 2,
        "seeing_index": 4,
        "seeing_forecast_at": "2026-07-17 09:00 PM",
        "transparency_index": 4,
        "transparency_forecast_at": "2026-07-17 09:00 PM",
    })
    difficult = score(weather={
        "cloud_cover_percent": 100,
        "humidity_percent": 100,
        "wind_speed_mph": 20,
        "seeing_index": 4,
        "seeing_forecast_at": "2026-07-17 09:00 PM",
        "transparency_index": 4,
        "transparency_forecast_at": "2026-07-17 09:00 PM",
    })

    assert component(clear, "seeing")["points"] == component(difficult, "seeing")["points"]
    assert component(clear, "visibility")["points"] == component(difficult, "visibility")["points"]


def test_missing_inputs_are_explicitly_unavailable_not_assumed_zero():
    payload = score(
        weather={"cloud_cover_percent": 20},
        moon={},
        darkness={"astronomical_darkness_start": "not-a-time"},
        target=None,
    )

    for key in ("cloud", "night", "moon", "visibility", "seeing", "altitude"):
        assert component(payload, key)["points"] is None


def test_total_uses_the_same_rounded_component_values_sent_to_clients():
    payload = score(
        weather={
            "cloud_cover_percent": 0,
            "humidity_percent": 50,
            "wind_speed_mph": 5,
            "transparency_index": 3,
            "transparency_forecast_at": "2026-07-17 09:00 PM",
            "seeing_index": 4,
            "seeing_forecast_at": "2026-07-17 09:00 PM",
        },
        moon={"illumination_percent": 50},
        darkness={
            "astronomical_darkness_start": "2026-07-17 08:00 PM",
            "astronomical_darkness_end": "2026-07-18 04:00 AM",
        },
        target={"maximum_dark_altitude": 55},
    )

    assert payload["total"] == 85
    assert payload["label"] == "Excellent"


def test_do_not_image_score_label_explains_hard_stop_without_hiding_components():
    payload = score(
        weather={
            "cloud_cover_percent": 100,
            "humidity_percent": 37,
            "wind_speed_mph": 11.5,
            "transparency_index": 2,
            "transparency_forecast_at": "2026-08-30 08:00 PM",
            "seeing_index": 3,
            "seeing_forecast_at": "2026-08-30 08:00 PM",
        },
        moon={"illumination_percent": 92.5},
        darkness={
            "astronomical_darkness_start": "2026-08-30 08:20 PM",
            "astronomical_darkness_end": "2026-08-31 04:34 AM",
        },
        target={"maximum_dark_altitude": 88.6},
    )

    explained = explain_opportunity_for_decision(payload, "Do Not Image")

    assert explained["total"] == 50.2
    assert explained["label"] == "No imaging window"
    assert "hard stop" in explained["guidance"]
    assert component(explained, "cloud")["points"] == 12.0
