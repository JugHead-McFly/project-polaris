from app.services.capture_analysis_service import calculate_quality_components
from app.services.capture_analysis_service import calculate_quality_components_v2
from app.services.capture_analysis_service import calculate_quality_score
from app.services.capture_analysis_service import build_quality_improvement_recommendation
from app.services.capture_analysis_service import build_quality_improvement_recommendation_v2


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


def test_quality_v2_scores_technical_measurements_without_star_count_points():
    components = calculate_quality_components_v2(
        object_name="M57",
        telescope="DWARF mini",
        star_sample_count=250,
        median_fwhm=2.03,
        median_roundness=0.102,
        median_star_snr=37.978,
        background_gradient=0.00805,
        clipped_pixel_fraction=0.0000072,
    )

    assert components == {
        "scoring_version": "2.0",
        "profile_label": "DWARF mini starter",
        "confidence": "high",
        "star_sample_count": 250,
        "median_fwhm": 2.03,
        "sharpness_points": 20,
        "median_roundness": 0.102,
        "roundness_points": 23,
        "median_star_snr": 37.978,
        "signal_points": 15,
        "background_gradient": 0.00805,
        "uniformity_points": 15,
        "clipped_pixel_fraction": 0.0000072,
        "clipping_points": 10,
        "quality_score": 83,
    }


def test_quality_v2_surfaces_soft_low_signal_capture():
    components = calculate_quality_components_v2(
        object_name="M22",
        telescope="DWARF mini",
        star_sample_count=99,
        median_fwhm=2.066,
        median_roundness=0.151,
        median_star_snr=9.531,
        background_gradient=0.453,
        clipped_pixel_fraction=0.0000014,
    )

    assert components["quality_score"] == 53
    assert components["sharpness_points"] == 19
    assert components["signal_points"] == 2
    assert components["uniformity_points"] == 4


def test_quality_v2_does_not_score_planets_with_deep_sky_model():
    components = calculate_quality_components_v2(
        object_name="JUPITER",
        telescope="DWARF mini",
        star_sample_count=6,
        median_fwhm=1.943,
        median_roundness=0.157,
        median_star_snr=34.772,
        background_gradient=6.9,
        clipped_pixel_fraction=0.0001845,
    )

    assert components["confidence"] == "unsupported"
    assert components["quality_score"] is None
    assert "planetary or lunar" in (
        build_quality_improvement_recommendation_v2(
            components
        )
    )
