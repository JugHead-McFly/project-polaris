from app.services.capture_analysis_service import calculate_quality_components
from app.services.capture_analysis_service import calculate_quality_score
from app.services.capture_analysis_service import build_quality_improvement_recommendation


def test_quality_score_exposes_the_same_component_points_used_in_total():
    components = calculate_quality_components(
        stars_detected=2500,
        median_value=10000,
        standard_deviation=500,
        trailing_detected=False,
    )

    assert components == {
        "base_points": 50,
        "star_points": 15,
        "background_points": 10,
        "variation_points": 15,
        "trailing_points": 5,
    }
    assert calculate_quality_score(
        stars_detected=2500,
        median_value=10000,
        standard_deviation=500,
        trailing_detected=False,
    ) == 95


def test_quality_score_remains_unavailable_without_analysis_metrics():
    assert calculate_quality_score(
        stars_detected=None,
        median_value=None,
        standard_deviation=None,
        trailing_detected=None,
    ) is None


def test_quality_recommendation_prioritizes_star_trailing():
    assert build_quality_improvement_recommendation(
        stars_detected=6000,
        median_value=10000,
        standard_deviation=500,
        trailing_detected=True,
    ) == (
        "Improve mount tracking or guiding before collecting more frames; "
        "star trailing had the largest impact on this image."
    )
