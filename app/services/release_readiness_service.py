import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from app.core.config import settings
from app.core.startup_preflight import run_startup_preflight
from app.services.backup_verification_service import verify_backup_pair


SMOKE_ENDPOINTS = {
    "/": "version",
    "/operator": None,
    "/system": "version",
    "/tonight": None,
    "/dashboard": "api_version",
}


def _check(
    name: str,
    passed: bool,
    message: str,
    details: Optional[Dict] = None,
) -> Dict:
    result = {
        "name": name,
        "status": "pass" if passed else "fail",
        "message": message,
    }
    if details is not None:
        result["details"] = details
    return result


def check_git_state(project_root: Path, expected_branch: str) -> Dict:
    try:
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        return _check(
            "source_state",
            False,
            f"Git source state could not be inspected: {error}",
        )

    branch = branch_result.stdout.strip()
    changes = [line for line in status_result.stdout.splitlines() if line]
    passed = branch == expected_branch and not changes
    if branch != expected_branch:
        message = f"Expected branch {expected_branch}, found {branch or 'detached HEAD'}."
    elif changes:
        message = f"Working tree has {len(changes)} uncommitted change(s)."
    else:
        message = f"Working tree is clean on {branch}."
    return _check(
        "source_state",
        passed,
        message,
        {"branch": branch, "change_count": len(changes)},
    )


def check_version(expected_version: str) -> Dict:
    passed = settings.VERSION == expected_version
    message = (
        f"Application version is {settings.VERSION}."
        if passed
        else (
            f"Expected application version {expected_version}, "
            f"found {settings.VERSION}."
        )
    )
    return _check(
        "application_version",
        passed,
        message,
        {
            "expected_version": expected_version,
            "application_version": settings.VERSION,
        },
    )


def check_startup_configuration() -> Dict:
    report = run_startup_preflight()
    return _check(
        "startup_preflight",
        report["ready"],
        (
            f"Startup preflight passed all {report['check_count']} checks."
            if report["ready"]
            else (
                "Startup preflight failed "
                f"{report['failure_count']} of {report['check_count']} checks."
            )
        ),
        report,
    )


def check_test_suite(project_root: Path, timeout_seconds: int = 300) -> Dict:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _check(
            "test_suite",
            False,
            f"Test suite exceeded the {timeout_seconds}-second timeout.",
        )
    except OSError as error:
        return _check(
            "test_suite",
            False,
            f"Test suite could not be started: {error}",
        )

    output_lines = [
        line.strip()
        for line in (result.stdout + "\n" + result.stderr).splitlines()
        if line.strip()
    ]
    summary = next(
        (line for line in reversed(output_lines) if " passed" in line),
        output_lines[-1] if output_lines else "No test output was produced.",
    )
    return _check(
        "test_suite",
        result.returncode == 0,
        summary,
        {"exit_code": result.returncode},
    )


def check_backup(backup_root: Path) -> Dict:
    report = verify_backup_pair(backup_root)
    message = (
        (
            f"Backup is valid: {report['matched_count']} captures matched, "
            "zero conflicts."
        )
        if report["valid"]
        else (
            "Backup verification failed: "
            f"{report['orphan_count']} orphan(s), "
            f"{report['missing_asset_count']} missing asset(s), "
            f"{report['conflict_count']} conflict(s)."
        )
    )
    return _check("backup_pair", report["valid"], message, report)


def check_live_endpoints(
    base_url: str,
    expected_version: str,
    timeout_seconds: int = 60,
) -> Dict:
    endpoint_results = []
    normalized_base_url = base_url.rstrip("/")

    for path, version_field in SMOKE_ENDPOINTS.items():
        url = f"{normalized_base_url}{path}"
        try:
            with urlopen(url, timeout=timeout_seconds) as response:
                status = response.status
                content_type = response.headers.get_content_type()
                body = response.read()
        except (HTTPError, URLError, OSError) as error:
            endpoint_results.append(
                {
                    "path": path,
                    "passed": False,
                    "message": str(error),
                }
            )
            continue

        passed = status == 200
        message = f"HTTP {status} ({content_type})"
        if passed and version_field is not None:
            try:
                payload = json.loads(body)
                actual_version = payload.get(version_field)
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                passed = False
                message = f"Response was not valid JSON: {error}"
            else:
                if actual_version != expected_version:
                    passed = False
                    message = (
                        f"Expected {version_field} {expected_version}, "
                        f"found {actual_version}."
                    )

        endpoint_results.append(
            {
                "path": path,
                "passed": passed,
                "message": message,
            }
        )

    failed = [result for result in endpoint_results if not result["passed"]]
    return _check(
        "live_smoke",
        not failed,
        (
            f"All {len(endpoint_results)} live endpoints passed."
            if not failed
            else f"{len(failed)} of {len(endpoint_results)} live endpoints failed."
        ),
        {"base_url": normalized_base_url, "endpoints": endpoint_results},
    )


def build_release_readiness_report(
    project_root: Path,
    backup_root: Path,
    base_url: str,
    expected_version: str,
    expected_branch: str = "develop",
    test_timeout_seconds: int = 300,
    smoke_timeout_seconds: int = 60,
) -> Dict:
    checks = [
        check_git_state(project_root, expected_branch),
        check_version(expected_version),
        check_startup_configuration(),
        check_test_suite(project_root, timeout_seconds=test_timeout_seconds),
        check_backup(backup_root),
        check_live_endpoints(
            base_url,
            expected_version,
            timeout_seconds=smoke_timeout_seconds,
        ),
    ]
    failures = [check for check in checks if check["status"] == "fail"]
    return {
        "ready": not failures,
        "status": "Release Ready" if not failures else "Blocked",
        "expected_version": expected_version,
        "check_count": len(checks),
        "failure_count": len(failures),
        "checks": checks,
        "failures": failures,
    }

