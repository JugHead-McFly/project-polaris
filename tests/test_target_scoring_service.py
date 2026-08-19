from app.data.rig_profiles import get_rig_profile
from app.services.target_scoring_service import TargetScoringInputs
from app.services.target_scoring_service import score_target_opportunity_for_rig
from app.services.target_scoring_service import score_target_opportunity


def test_strong_target_opportunity_scores_high():
    result = score_target_opportunity(
        TargetScoringInputs(
            maximum_altitude_degrees=72,
            usable_dark_minutes=260,
            moon_illumination_percent=18,
            moon_separation_degrees=110,
            bortle_class=3,
            target_fits_field_of_view=True,
            exposure_confidence=0.92,
        )
    )

    assert result.score == 100
    assert result.quality == "Excellent opportunity"
    assert [component.label for component in result.components] == [
        "Altitude",
        "Usable window",
        "Moon",
        "Sky brightness",
        "Field of view",
        "Exposure confidence",
    ]


def test_poor_target_opportunity_scores_low():
    result = score_target_opportunity(
        TargetScoringInputs(
            maximum_altitude_degrees=18,
            usable_dark_minutes=35,
            moon_illumination_percent=91,
            moon_separation_degrees=22,
            bortle_class=8,
            target_fits_field_of_view=False,
            exposure_confidence=0.2,
        )
    )

    assert result.score == 0
    assert result.quality == "Poor opportunity"
    assert any(
        component.label == "Field of view" and component.points == -30
        for component in result.components
    )


def test_unknown_inputs_remain_neutral_or_cautious():
    result = score_target_opportunity(
        TargetScoringInputs(
            maximum_altitude_degrees=None,
            usable_dark_minutes=150,
            moon_illumination_percent=None,
            moon_separation_degrees=None,
            bortle_class=None,
            target_fits_field_of_view=None,
            exposure_confidence=None,
        )
    )

    assert result.score == 35
    assert result.quality == "Poor opportunity"
    assert any(
        component.label == "Sky brightness" and component.points == 0
        for component in result.components
    )


def test_rig_aware_scoring_rewards_comfortable_framing():
    result = score_target_opportunity_for_rig(
        rig=get_rig_profile("DWARF 3"),
        target_width_degrees=2.0,
        target_height_degrees=1.1,
        maximum_altitude_degrees=58,
        usable_dark_minutes=210,
        moon_illumination_percent=22,
        moon_separation_degrees=95,
        bortle_class=4,
        exposure_confidence=0.75,
    )

    field_component = next(
        component for component in result.components if component.label == "Field of view"
    )
    assert field_component.points == 10
    assert result.quality == "Excellent opportunity"


def test_rig_aware_scoring_treats_tiny_targets_as_weaker_fit():
    comfortable = score_target_opportunity_for_rig(
        rig=get_rig_profile("DWARF 3"),
        target_width_degrees=2.0,
        target_height_degrees=1.1,
        maximum_altitude_degrees=58,
        usable_dark_minutes=210,
        moon_illumination_percent=22,
        moon_separation_degrees=95,
        bortle_class=4,
        exposure_confidence=0.75,
    )
    tiny = score_target_opportunity_for_rig(
        rig=get_rig_profile("DWARF 3"),
        target_width_degrees=0.25,
        target_height_degrees=0.18,
        maximum_altitude_degrees=58,
        usable_dark_minutes=210,
        moon_illumination_percent=22,
        moon_separation_degrees=95,
        bortle_class=4,
        exposure_confidence=0.75,
    )

    comfortable_field = next(
        component for component in comfortable.components if component.label == "Field of view"
    )
    tiny_field = next(
        component for component in tiny.components if component.label == "Field of view"
    )

    assert comfortable_field.points - tiny_field.points == 8
    assert any(
        component.label == "Field of view"
        and component.points == 2
        and "small" in component.reason
        for component in tiny.components
    )


def test_rig_aware_scoring_penalizes_targets_too_large_for_the_rig():
    result = score_target_opportunity_for_rig(
        rig=get_rig_profile("Seestar S50"),
        target_width_degrees=2.0,
        target_height_degrees=1.0,
        maximum_altitude_degrees=58,
        usable_dark_minutes=210,
        moon_illumination_percent=22,
        moon_separation_degrees=95,
        bortle_class=4,
        exposure_confidence=0.75,
    )

    assert any(
        component.label == "Field of view" and component.points == -30
        for component in result.components
    )
