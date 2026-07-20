import pytest

from app.services.goal_engine_service import build_integration_goal


def test_goal_engine_uses_target_class_instead_of_a_generic_default():
    galaxy = build_integration_goal("M51")
    open_cluster = build_integration_goal("M11")

    assert galaxy["hours"] == 8.0
    assert open_cluster["hours"] == 2.0
    assert "galaxy" in galaxy["note"]
    assert "open cluster" in open_cluster["note"]


def test_goal_engine_exposes_quick_detailed_and_showcase_aims():
    goal = build_integration_goal("M16")

    assert goal["tier"] == "detailed"
    assert [(option["tier"], option["hours"]) for option in goal["options"]] == [
        ("quick", 3.0),
        ("detailed", 6.0),
        ("showcase", 12.0),
    ]
    assert "not an image-quality score" in goal["note"]


def test_goal_engine_applies_explainable_object_adjustments():
    ring_nebula = build_integration_goal("M57")
    owl_nebula = build_integration_goal("M97")

    assert ring_nebula["hours"] == 4.0
    assert owl_nebula["hours"] == 6.0
    assert any("compact, bright ring" in factor for factor in ring_nebula["factors"])


def test_goal_engine_rejects_an_unknown_aim():
    with pytest.raises(ValueError, match="Unknown integration-goal tier"):
        build_integration_goal("M51", tier="impossible")


def test_goal_engine_does_not_apply_a_deep_sky_default_to_moving_targets():
    jupiter = build_integration_goal("JUPITER")
    comet = build_integration_goal("C 2026 B3 PANSTARRS")

    assert jupiter["hours"] == 1.0
    assert [option["hours"] for option in jupiter["options"]] == [0.5, 1.0, 2.0]
    assert "atmospheric steadiness" in jupiter["note"]
    assert comet["hours"] == 2.0
    assert "change over time" in comet["note"]
