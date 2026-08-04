from app.services.target_scoring_service import TargetScoringInputs
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
