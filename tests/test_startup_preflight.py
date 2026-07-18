import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.startup_preflight import format_preflight_failure
from app.core.startup_preflight import run_startup_preflight
from app.main import app


def create_runtime_layout(tmp_path: Path):
    base_dir = tmp_path / "dougs-observatory"
    web_directory = base_dir / "app" / "web"
    web_directory.mkdir(parents=True)
    for filename in ("operator.css", "operator.html", "operator.js"):
        (web_directory / filename).write_text(filename)

    database_file = base_dir / "polaris.db"
    connection = sqlite3.connect(database_file)
    for table_name in ("captures", "sessions", "capture_analyses"):
        connection.execute(f"CREATE TABLE {table_name} (id INTEGER)")
    connection.commit()
    connection.close()

    library_root = tmp_path / "ProjectPolaris"
    (library_root / "targets").mkdir(parents=True)
    return base_dir, database_file, library_root, web_directory


def test_valid_startup_configuration_is_ready(tmp_path):
    base_dir, database_file, library_root, web_directory = (
        create_runtime_layout(tmp_path)
    )

    report = run_startup_preflight(
        base_dir=base_dir,
        database_file=database_file,
        database_url=f"sqlite:///{database_file}",
        library_root=library_root,
        log_level="INFO",
        web_directory=web_directory,
    )

    assert report["ready"]
    assert report["status"] == "Ready"
    assert report["failure_count"] == 0
    assert report["check_count"] == 7
    assert {check["status"] for check in report["checks"]} == {"pass"}


def test_preflight_reports_all_independent_configuration_failures(tmp_path):
    base_dir, database_file, library_root, web_directory = (
        create_runtime_layout(tmp_path)
    )
    (web_directory / "operator.js").unlink()

    report = run_startup_preflight(
        base_dir=base_dir,
        database_file=database_file,
        database_url=f"sqlite:///{database_file}",
        library_root=library_root / "missing",
        log_level="VERBOSE",
        web_directory=web_directory,
    )

    assert not report["ready"]
    assert report["status"] == "Blocked"
    assert {failure["name"] for failure in report["failures"]} == {
        "capture_library",
        "capture_targets",
        "log_level",
        "web_assets",
    }


def test_preflight_rejects_database_url_and_schema_mismatches(tmp_path):
    base_dir, database_file, library_root, web_directory = (
        create_runtime_layout(tmp_path)
    )
    connection = sqlite3.connect(database_file)
    connection.execute("DROP TABLE capture_analyses")
    connection.commit()
    connection.close()

    report = run_startup_preflight(
        base_dir=base_dir,
        database_file=database_file,
        database_url="sqlite:////different/polaris.db",
        library_root=library_root,
        log_level="DEBUG",
        web_directory=web_directory,
    )

    failures = {failure["name"]: failure for failure in report["failures"]}
    assert set(failures) == {"database", "database_url"}
    assert "does not match DATABASE_FILE" in failures["database_url"]["message"]
    assert "capture_analyses" in failures["database"]["message"]


def test_preflight_failure_message_is_operator_readable():
    report = {
        "failures": [
            {
                "name": "database",
                "status": "fail",
                "message": "Database file was not found: /missing/polaris.db",
            }
        ]
    }

    message = format_preflight_failure(report)

    assert message.startswith("Project Polaris startup preflight failed:")
    assert "database: Database file was not found" in message


def test_application_lifespan_refuses_failed_preflight():
    report = {
        "ready": False,
        "checks": [
            {
                "name": "database",
                "status": "fail",
                "message": "Database file was not found.",
            }
        ],
        "failures": [
            {
                "name": "database",
                "status": "fail",
                "message": "Database file was not found.",
            }
        ],
    }

    with patch("app.main.run_startup_preflight", return_value=report):
        with pytest.raises(RuntimeError, match="startup preflight failed"):
            with TestClient(app):
                pass
