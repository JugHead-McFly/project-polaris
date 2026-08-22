from app.services.imaging_settings_service import apply_tonight_settings
from app.services.imaging_settings_service import recommend_imaging_settings


def _recommend(
    object_name,
    *,
    exposure=15,
    gain=60,
    filter_name="Astro",
    source="catalog",
    weather=None,
    moon=None,
    moon_warning="Minimal",
    moon_separation=90,
    bortle=5,
    equatorial_mode=None,
    rig_profile_key=None,
):
    return recommend_imaging_settings(
        object_name=object_name,
        base_exposure_seconds=exposure,
        base_gain=gain,
        base_filter=filter_name,
        recommendation_source=source,
        weather=weather or {},
        moon=moon or {"illumination_percent": 10},
        moon_warning=moon_warning,
        moon_separation_degrees=moon_separation,
        bortle_class=bortle,
        equatorial_mode_enabled=equatorial_mode,
        rig_profile_key=rig_profile_key,
    )


def test_emission_nebula_stays_at_normal_mode_limit_without_eq_confirmation():
    settings = _recommend(
        "C20",
        weather={
            "wind_speed_mph": 14,
            "planned_wind_speed_mph": 4,
        },
        moon={"illumination_percent": 85},
        moon_warning="High",
        moon_separation=32,
        bortle=7,
    )

    assert settings["filter"] == "Duo-Band"
    assert settings["sub_exposure_seconds"] == 15
    assert settings["gain"] == 60
    assert settings["confidence_label"] == "Beginner-safe starting point"
    assert any(
        "has not been told that equatorial tracking is enabled" in reason
        for reason in settings["reasons"]
    )
    assert any(
        "DWARF's normal tracking mode is limited to 15 seconds" in reason
        for reason in settings["reasons"]
    )


def test_selected_seestar_uses_its_supported_ten_second_subs():
    settings = _recommend(
        "C20",
        exposure=15,
        filter_name="Duo-Band",
        weather={"planned_wind_speed_mph": 3},
        moon={"illumination_percent": 80},
        moon_warning="High",
        moon_separation=35,
        bortle=7,
        equatorial_mode=False,
        rig_profile_key="seestar-s50",
    )

    assert settings["sub_exposure_seconds"] == 10
    assert not any("DWARF" in reason for reason in settings["reasons"])
    assert any(
        "Start with 10-second exposures" in reason
        for reason in settings["reasons"]
    )


def test_selected_seestar_weather_reasons_match_its_ten_second_subs():
    windy_settings = _recommend(
        "M16",
        exposure=60,
        source="best_capture",
        weather={"planned_wind_speed_mph": 13},
        rig_profile_key="seestar-s50",
    )

    assert windy_settings["sub_exposure_seconds"] == 10
    assert any(
        "Use 10-second exposures because strong wind" in reason
        for reason in windy_settings["reasons"]
    )
    assert not any(
        "Use 15-second exposures" in reason
        for reason in windy_settings["reasons"]
    )

    moon_settings = _recommend(
        "M31",
        exposure=60,
        filter_name="Duo-Band",
        weather={"planned_wind_speed_mph": 2},
        moon={"illumination_percent": 90},
        moon_warning="High",
        moon_separation=35,
        rig_profile_key="seestar-s50",
    )

    assert moon_settings["sub_exposure_seconds"] == 10
    assert any(
        "Use 10-second exposures so Moon or city glow" in reason
        for reason in moon_settings["reasons"]
    )
    assert not any(
        "Use 15-second exposures" in reason
        for reason in moon_settings["reasons"]
    )


def test_emission_nebula_can_use_longer_subs_when_eq_is_confirmed():
    settings = _recommend(
        "C20",
        weather={"planned_wind_speed_mph": 4},
        moon={"illumination_percent": 85},
        moon_warning="High",
        moon_separation=32,
        bortle=7,
        equatorial_mode=True,
    )

    assert settings["filter"] == "Duo-Band"
    assert settings["sub_exposure_seconds"] == 30
    assert "exposure" in settings["adjustments"]
    assert any(
        "Equatorial tracking is confirmed" in reason
        for reason in settings["reasons"]
    )


def test_broadband_target_uses_astro_and_short_subs_under_bright_moon():
    settings = _recommend(
        "M31",
        exposure=60,
        filter_name="Duo-Band",
        weather={"planned_wind_speed_mph": 2},
        moon={"illumination_percent": 90},
        moon_warning="High",
        moon_separation=35,
    )

    assert settings["filter"] == "Astro"
    assert settings["sub_exposure_seconds"] == 15
    assert settings["adjustments"] == ["exposure", "filter"]


def test_strong_forecast_wind_forces_short_subs():
    settings = _recommend(
        "M16",
        exposure=60,
        source="best_capture",
        weather={"planned_wind_speed_mph": 13},
    )

    assert settings["sub_exposure_seconds"] == 15
    assert settings["confidence_label"] == "Capture history adjusted for tonight"


def test_moderate_forecast_wind_caps_subs_at_thirty_seconds():
    settings = _recommend(
        "M16",
        exposure=60,
        source="best_capture",
        weather={"planned_wind_speed_mph": 9},
        equatorial_mode=True,
    )

    assert settings["sub_exposure_seconds"] == 30


def test_calm_successful_history_is_retained():
    settings = _recommend(
        "M57",
        exposure=15,
        gain=80,
        filter_name="Duo-Band",
        source="best_capture",
        weather={"planned_wind_speed_mph": 3},
    )

    assert settings["sub_exposure_seconds"] == 15
    assert settings["gain"] == 80
    assert settings["filter"] == "Duo-Band"
    assert settings["confidence_label"] == "Based on your capture history"


def test_eq_confirmation_can_improve_calm_successful_nebula_history():
    settings = _recommend(
        "C20",
        exposure=15,
        gain=60,
        filter_name="Duo-Band",
        source="best_capture",
        weather={"planned_wind_speed_mph": 3},
        equatorial_mode=True,
    )

    assert settings["sub_exposure_seconds"] == 30
    assert settings["gain"] == 60
    assert settings["filter"] == "Duo-Band"
    assert settings["confidence_label"] == "Capture history adjusted for tonight"
    assert any(
        "successful 15-second setting remains the safer fallback" in reason
        for reason in settings["reasons"]
    )


def test_unconfirmed_eq_caps_a_long_historical_exposure_at_fifteen_seconds():
    settings = _recommend(
        "C20",
        exposure=30,
        gain=60,
        filter_name="Duo-Band",
        source="best_capture",
        weather={"planned_wind_speed_mph": 3},
        equatorial_mode=False,
    )

    assert settings["sub_exposure_seconds"] == 15
    assert settings["confidence_label"] == "Capture history adjusted for tonight"
    assert any(
        "equatorial tracking is not confirmed" in reason
        for reason in settings["reasons"]
    )


def test_clouds_do_not_lengthen_the_exposure_recipe():
    settings = _recommend(
        "M31",
        exposure=30,
        source="best_capture",
        weather={
            "planned_cloud_cover_percent": 60,
            "planned_wind_speed_mph": 2,
        },
        moon={"illumination_percent": 5},
        equatorial_mode=True,
    )

    assert settings["sub_exposure_seconds"] == 30
    assert any("cannot collect light that a cloud has blocked" in reason for reason in settings["reasons"])


def test_bright_moon_below_horizon_does_not_force_a_moon_override():
    settings = _recommend(
        "M31",
        exposure=30,
        source="best_capture",
        weather={"planned_wind_speed_mph": 2},
        moon={"illumination_percent": 95},
        moon_warning="None — Moon below the horizon",
        moon_separation=20,
        bortle=4,
        equatorial_mode=True,
    )

    assert settings["sub_exposure_seconds"] == 30
    assert settings["confidence_label"] == "Based on your capture history"


def test_heat_adds_dark_frame_guidance_without_raising_gain():
    settings = _recommend(
        "M57",
        gain=60,
        source="best_capture",
        weather={
            "planned_temperature_f": 98,
            "planned_wind_speed_mph": 2,
        },
    )

    assert settings["gain"] == 60
    assert any("session temperature" in item for item in settings["setup_guidance"])


def test_applying_settings_recalculates_remaining_frame_count():
    advisor = {
        "object": "C20",
        "remaining_seconds": 3600,
        "recommended_sub_exposure_seconds": 15,
        "recommended_gain": 60,
        "recommended_filter": "Astro",
        "recommendation_source": "catalog",
    }

    updated = apply_tonight_settings(
        advisor=advisor,
        weather={"planned_wind_speed_mph": 2},
        moon={"illumination_percent": 80},
        moon_warning="High",
        moon_separation_degrees=30,
        bortle_class=7,
        equatorial_mode_enabled=True,
    )

    assert updated["recommended_sub_exposure_seconds"] == 30
    assert updated["additional_subframes_needed"] == 120
    assert updated["recommended_filter"] == "Duo-Band"
