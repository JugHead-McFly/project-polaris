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
    assert "sensor noise curve is not included" in seestar.notes


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
