from scripts.alpha_metrics_report import render_text_report


def test_text_alpha_metrics_report_summarizes_without_private_details():
    report = {
        "accounts": {
            "profiles_created": 2,
            "with_observing_home": 2,
            "with_saved_plan": 1,
            "returning_for_two_or_more_nights": 0,
        },
        "activation": {
            "observing_home_rate_percent": 100.0,
            "first_plan_rate_percent": 50.0,
            "returning_planner_rate_percent": 0.0,
        },
        "recommendations": {
            "saved": 1,
            "by_outcome": {"Do Not Image": 1},
            "first_saved_at": "2026-08-02T20:00:00+00:00",
            "last_saved_at": "2026-08-02T20:00:00+00:00",
        },
        "feedback": {
            "responses": 1,
            "useful": 0,
            "not_useful": 1,
            "response_rate_percent": 100.0,
        },
        "review_focus": {
            "priority": "Recommendation trust",
            "reason": "At least one usefulness response says the plan was not useful.",
        },
    }

    rendered = render_text_report(report)

    assert "Review focus: Recommendation trust" in rendered
    assert "First-plan rate: 50.0%" in rendered
    assert "Outcomes: Do Not Image=1" in rendered
    assert "Privacy: aggregate counts only" in rendered
    assert "2026-08-02T20:00:00+00:00" not in rendered
    assert "Alice" not in rendered
