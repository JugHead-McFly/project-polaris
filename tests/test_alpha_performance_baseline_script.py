from scripts.alpha_performance_baseline import TimingResult
from scripts.alpha_performance_baseline import render_report


def test_performance_baseline_report_is_internal_and_aggregate():
    report = render_report(
        {
            "/health/live": [
                TimingResult(
                    path="/health/live",
                    status=200,
                    elapsed_ms=100.4,
                    ok=True,
                ),
                TimingResult(
                    path="/health/live",
                    status=200,
                    elapsed_ms=200.6,
                    ok=True,
                ),
            ],
            "/operator": [
                TimingResult(
                    path="/operator",
                    status=None,
                    elapsed_ms=500.2,
                    ok=False,
                    error="timed out",
                )
            ],
        }
    )

    assert "Project Polaris alpha performance baseline" in report
    assert "/health/live" in report
    assert "Successful: 2/2" in report
    assert "Median: 150 ms" in report
    assert "Statuses: error" in report
    assert "Errors: timed out" in report
    assert "Do not ask alpha testers to collect these numbers." in report
