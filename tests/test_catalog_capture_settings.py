import pytest

from app.services.advisor_service import get_catalog_exposure_advice
from app.services.imaging_settings_service import apply_tonight_settings
from app.services.portfolio_service import get_target_metadata
from app.services.capture_history_service import history_advice
from app.data.targets import get_target_common_name


def settings(name, rig="dwarf-mini", advisor=None, **kwargs):
    return apply_tonight_settings(
        advisor=advisor or get_catalog_exposure_advice(name),
        weather={}, moon={"illumination_percent": 10}, moon_warning="Minimal",
        moon_separation_degrees=90, bortle_class=5, rig_profile_key=rig, **kwargs)


@pytest.mark.parametrize("ngc,messier", [("NGC7092", "M39"), ("NGC1039", "M34"), ("NGC2099", "M37")])
def test_reported_clusters_receive_identical_alias_starting_exposure(ngc, messier):
    assert messier in get_target_common_name(ngc)
    first, second = settings(ngc), settings(messier)
    for result in (first, second):
        assert result["recommended_sub_exposure_seconds"] == 15
        assert result["recommended_gain"] == 60
        assert result["recommended_filter"] == "Astro"
        assert result["recommendation_source"] == "rig_category_starting_point"
        assert "not capture-calibrated" in result["settings_confidence"]
        assert result["settings_provenance"]["capture_history_used"] is False
        assert result["settings_provenance"]["rig_profile_key"] == "dwarf-mini"
        assert result["settings_provenance"]["user_configuration_read"] is False
        assert result["settings_provenance"]["manufacturer_default_claimed"] is False
        assert "not a recovered user setting" in " ".join(result["settings_reasons"])
        assert result["additional_subframes_needed"] > 0


def test_curated_recipe_resolves_ngc_alias_without_rewriting_it():
    for name in ("NGC6705", "NGC 6705", "M11"):
        metadata = get_target_metadata(name)
        assert (metadata["exposure_seconds"], metadata["gain"], metadata["recommended_filter"]) == (10, 60, "Astro")
        assert metadata["settings_preset_target"] == "M11"
        assert get_catalog_exposure_advice(name)["object"] == name.upper()


@pytest.mark.parametrize("name,filter_name", [("NGC7092", "Astro"), ("NGC7000", "Duo-Band")])
@pytest.mark.parametrize("rig", ["dwarf-mini", "dwarf-3"])
@pytest.mark.parametrize("bortle", [3, 7])
def test_recorded_category_capabilities(name, filter_name, rig, bortle):
    # Emission filter is selected in light polluted conditions.
    advice = get_catalog_exposure_advice(name)
    result = apply_tonight_settings(advisor=advice, weather={}, moon={}, moon_warning="Minimal",
        moon_separation_degrees=90, bortle_class=bortle, rig_profile_key=rig)
    assert result["recommended_sub_exposure_seconds"] == 15
    assert result["recommended_gain"] == 60
    assert result["recommended_filter"] == filter_name


@pytest.mark.parametrize("rig", [None, "unknown-rig", "hestia"])
def test_missing_capabilities_do_not_invent_settings(rig):
    result = settings("NGC7092", rig)
    assert result["recommended_sub_exposure_seconds"] is None
    assert result["recommended_gain"] is None
    assert result["recommended_filter"] is None


def test_alias_history_progress_remains_intact_and_ungraded():
    advice = history_advice("NGC7092", {"M39": {"seconds": 3600}})
    result = settings("NGC7092", advisor=advice)
    assert result["current_integration_seconds"] == 3600
    assert result["remaining_seconds"] == advice["remaining_seconds"]
    assert result["source_capture_id"] is None
    assert result["settings_provenance"]["capture_history_used"] is False


def test_explicit_successful_capture_recipe_keeps_precedence():
    advice = {**get_catalog_exposure_advice("M39"), "recommendation_source": "best_capture",
              "recommended_sub_exposure_seconds": 30, "recommended_gain": 75,
              "recommended_filter": "Astro", "source_capture_id": 123}
    result = settings("M39", advisor=advice, equatorial_mode_enabled=True)
    assert (result["recommended_sub_exposure_seconds"], result["recommended_gain"], result["recommended_filter"]) == (30, 75, "Astro")
    assert result["source_capture_id"] == 123
    assert result["settings_provenance"]["capture_history_used"] is True
