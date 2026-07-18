import json
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from app.core.config import settings
from app.services.release_readiness_service import (
    build_release_readiness_report,
)
from app.services.release_readiness_service import check_live_endpoints
from app.services.release_readiness_service import check_test_suite
from app.services.release_readiness_service import check_version


def passing_check(name):
    return {
        "name": name,
        "status": "pass",
        "message": "passed",
    }


def fake_response(path: str, expected_version: str):
    response = MagicMock()
    response.status = 200
    response.headers.get_content_type.return_value = (
        "text/html" if path == "/operator" else "application/json"
    )
    payload = {}
    if path in {"/", "/system"}:
        payload["version"] = expected_version
    elif path == "/dashboard":
        payload["api_version"] = expected_version
    response.read.return_value = json.dumps(payload).encode()
    response.__enter__.return_value = response
    return response


def test_version_gate_requires_exact_release_version():
    matching = check_version(settings.VERSION)
    mismatched = check_version("99.0.0")

    assert matching["status"] == "pass"
    assert mismatched["status"] == "fail"
    assert mismatched["details"]["application_version"] == settings.VERSION


def test_live_smoke_requires_all_endpoints_and_versions():
    expected_version = settings.VERSION

    def open_endpoint(url, timeout):
        path = url.removeprefix("http://127.0.0.1:8000")
        return fake_response(path, expected_version)

    with patch(
        "app.services.release_readiness_service.urlopen",
        side_effect=open_endpoint,
    ):
        report = check_live_endpoints(
            "http://127.0.0.1:8000",
            expected_version,
        )

    assert report["status"] == "pass"
    assert len(report["details"]["endpoints"]) == 5
    assert all(
        endpoint["passed"]
        for endpoint in report["details"]["endpoints"]
    )


def test_live_smoke_rejects_version_drift():
    response = fake_response("/", "0.0.0")
    with patch(
        "app.services.release_readiness_service.urlopen",
        return_value=response,
    ):
        report = check_live_endpoints(
            "http://127.0.0.1:8000",
            settings.VERSION,
        )

    assert report["status"] == "fail"
    failed = [
        endpoint
        for endpoint in report["details"]["endpoints"]
        if not endpoint["passed"]
    ]
    assert {endpoint["path"] for endpoint in failed} == {
        "/",
        "/system",
        "/dashboard",
    }


def test_quiet_test_success_has_a_clear_summary(tmp_path):
    completed = MagicMock(
        returncode=0,
        stdout="................................ [100%]\n",
        stderr="",
    )
    with patch(
        "app.services.release_readiness_service.subprocess.run",
        return_value=completed,
    ):
        report = check_test_suite(tmp_path)

    assert report["status"] == "pass"
    assert report["message"] == "Test suite passed."


@patch("app.services.release_readiness_service.check_live_endpoints")
@patch("app.services.release_readiness_service.check_backup")
@patch("app.services.release_readiness_service.check_test_suite")
@patch("app.services.release_readiness_service.check_startup_configuration")
@patch("app.services.release_readiness_service.check_version")
@patch("app.services.release_readiness_service.check_git_state")
def test_release_report_is_ready_only_when_every_gate_passes(
    git_check,
    version_check,
    startup_check,
    test_check,
    backup_check,
    live_check,
    tmp_path,
):
    checks = [
        (git_check, "source_state"),
        (version_check, "application_version"),
        (startup_check, "startup_preflight"),
        (test_check, "test_suite"),
        (backup_check, "backup_pair"),
        (live_check, "live_smoke"),
    ]
    for mock, name in checks:
        mock.return_value = passing_check(name)

    report = build_release_readiness_report(
        project_root=tmp_path,
        backup_root=tmp_path / "backup",
        base_url="http://127.0.0.1:8000",
        expected_version=settings.VERSION,
    )
    assert report["ready"]
    assert report["status"] == "Release Ready"

    backup_check.return_value = {
        "name": "backup_pair",
        "status": "fail",
        "message": "invalid",
    }
    blocked = build_release_readiness_report(
        project_root=tmp_path,
        backup_root=tmp_path / "backup",
        base_url="http://127.0.0.1:8000",
        expected_version=settings.VERSION,
    )
    assert not blocked["ready"]
    assert blocked["status"] == "Blocked"
    assert blocked["failure_count"] == 1
