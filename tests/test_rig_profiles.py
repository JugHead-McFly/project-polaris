from app.data.rig_profiles import RIG_PROFILES
from app.data.rig_profiles import get_rig_profile


def test_starter_rig_profiles_include_core_alpha_devices():
    assert {"dwarf-3", "seestar-s50", "seestar-s30", "vespera-ii"}.issubset(
        RIG_PROFILES
    )


def test_rig_profile_lookup_accepts_key_or_model_name():
    assert get_rig_profile("dwarf-3").model == "DWARF 3"
    assert get_rig_profile("DWARF 3").key == "dwarf-3"
    assert get_rig_profile("Seestar S50").key == "seestar-s50"
    assert get_rig_profile("unknown") is None


def test_dwarf_profile_keeps_conservative_planning_limits():
    profile = get_rig_profile("DWARF 3")

    assert profile.aperture_mm == 35
    assert profile.focal_length_mm == 150
    assert profile.sensor_name == "Sony IMX678 STARVIS 2"
    assert profile.default_gain == 60
    assert profile.frame_limit == 999
    assert profile.storage_gb == 128
    assert profile.battery_life_hours == 5.5
    assert profile.operating_temperature_c == (-20, 45)
    assert 15 in profile.supported_exposures_seconds
    assert profile.read_noise_electrons == 0.6
    assert profile.confidence == "manufacturer_and_help_center"


def test_rig_profiles_keep_sources_and_uncertainty_visible():
    for profile in RIG_PROFILES.values():
        assert profile.source_urls
        assert profile.confidence

    seestar = get_rig_profile("Seestar S50")
    assert seestar.read_noise_electrons is None
    assert seestar.full_well_electrons is None
    assert seestar.battery_life_hours == 6
    assert seestar.storage_gb == 64
    assert seestar.operating_temperature_c == (-10, 40)
    assert "single-run frame limit" in seestar.notes


def test_vaonis_profile_records_dew_heater_battery_limit():
    vespera = get_rig_profile("Vespera II")

    assert vespera.storage_gb == 25
    assert vespera.battery_life_hours == 4
    assert vespera.dew_heater_battery_life_hours == 2.5


def test_field_dimensions_are_ordered_for_matching_targets():
    vespera = get_rig_profile("vespera-ii")

    assert vespera.field_width_degrees == 2.5
    assert vespera.field_height_degrees == 1.4


def test_rig_profile_assesses_comfortable_target_fit():
    profile = get_rig_profile("DWARF 3")

    fit = profile.assess_target_fit(target_width_degrees=2.0, target_height_degrees=1.1)

    assert fit.fits is True
    assert fit.label == "Comfortable fit"
    assert fit.margin_degrees == 0.8


def test_rig_profile_flags_oversized_targets():
    profile = get_rig_profile("Seestar S50")

    fit = profile.assess_target_fit(target_width_degrees=2.0, target_height_degrees=1.0)

    assert fit.fits is False
    assert fit.label == "Too large"
    assert fit.margin_degrees == -0.71


def test_rig_profile_flags_tiny_targets_separately_from_bad_fit():
    profile = get_rig_profile("DWARF 3")

    fit = profile.assess_target_fit(target_width_degrees=0.25, target_height_degrees=0.18)

    assert fit.fits is True
    assert fit.label == "Very small"


def test_rig_profile_keeps_unknown_target_fit_explicit():
    profile = get_rig_profile("DWARF 3")

    fit = profile.assess_target_fit(target_width_degrees=None, target_height_degrees=1.0)

    assert fit.fits is None
    assert fit.label == "Unknown fit"


def test_rig_profile_estimates_single_run_inside_frame_limit():
    profile = get_rig_profile("DWARF 3")

    plan = profile.estimate_run_plan(imaging_minutes=240, sub_exposure_seconds=30)

    assert plan.total_frames == 480
    assert plan.run_count == 1
    assert plan.frames_per_run == 480
    assert plan.label == "Single run"


def test_rig_profile_estimates_split_runs_when_frame_limit_is_exceeded():
    profile = get_rig_profile("DWARF 3")

    plan = profile.estimate_run_plan(imaging_minutes=600, sub_exposure_seconds=30)

    assert plan.total_frames == 1200
    assert plan.run_count == 2
    assert plan.frames_per_run == 999
    assert plan.label == "Split run"


def test_rig_profile_keeps_unknown_frame_limits_explicit():
    profile = get_rig_profile("Seestar S50")

    plan = profile.estimate_run_plan(imaging_minutes=240, sub_exposure_seconds=10)

    assert plan.total_frames == 1440
    assert plan.run_count is None
    assert plan.frames_per_run is None
    assert plan.label == "Frame limit unknown"


def test_rig_profile_rejects_non_positive_run_inputs_without_guessing():
    profile = get_rig_profile("DWARF 3")

    plan = profile.estimate_run_plan(imaging_minutes=0, sub_exposure_seconds=30)

    assert plan.total_frames == 0
    assert plan.run_count == 0
    assert plan.label == "No frames"
