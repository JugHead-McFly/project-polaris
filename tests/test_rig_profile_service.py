from app.services.rig_profile_service import list_rig_profile_summaries
from app.services.rig_profile_service import summarize_rig_profile_catalog


def test_rig_profile_catalog_summary_counts_current_database():
    summary = summarize_rig_profile_catalog()

    assert summary.total_profiles == 17
    assert summary.manufacturers == [
        "Celestron",
        "DWARFLAB",
        "Unistellar",
        "Vaonis",
        "ZWO",
    ]
    assert summary.profiles_with_field_of_view == 14
    assert summary.profiles_with_battery_limit == 14
    assert summary.profiles_with_storage_limit == 13
    assert summary.profiles_with_temperature_limit == 5
    assert summary.profiles_with_frame_limit == 1


def test_rig_profile_summaries_are_sorted_and_plain_language_ready():
    summaries = list_rig_profile_summaries()

    assert summaries[0].key == "celestron-origin"
    assert summaries[0].label == "Celestron Origin Intelligent Home Observatory"
    assert summaries[-1].key == "seestar-s50"
    assert summaries[-1].manufacturer == "ZWO"


def test_rig_profile_summary_keeps_unknown_limits_visible():
    summaries = {summary.key: summary for summary in list_rig_profile_summaries()}

    assert summaries["dwarf-3"].has_frame_limit is True
    assert summaries["dwarf-3"].has_equatorial_tracking is True
    assert summaries["seestar-s50"].has_frame_limit is False
    assert summaries["seestar-s50"].has_equatorial_tracking is False
    assert summaries["hestia"].has_battery_limit is False
    assert summaries["dwarf-mini"].has_field_of_view is False
