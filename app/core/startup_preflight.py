import logging
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.storage import POLARIS_ROOT
from app.database.database import engine_options


LOCAL_REQUIRED_DATABASE_TABLES = {
    "capture_analyses",
    "captures",
    "sessions",
}
HOSTED_REQUIRED_DATABASE_TABLES = {
    "observatories",
    "profiles",
    "recommendation_feedback",
    "recommendation_runs",
}
REQUIRED_WEB_ASSETS = {
    "operator.css",
    "operator.html",
    "operator.js",
}
VALID_LOG_LEVELS = {
    "CRITICAL",
    "DEBUG",
    "ERROR",
    "INFO",
    "NOTSET",
    "WARNING",
}


def _check(name: str, status: str, message: str) -> Dict[str, str]:
    return {
        "name": name,
        "status": status,
        "message": message,
    }


def _check_directory(
    name: str,
    path: Path,
) -> Dict[str, str]:
    if not path.is_dir():
        return _check(name, "fail", f"Required directory was not found: {path}")
    if not os.access(path, os.R_OK | os.X_OK):
        return _check(name, "fail", f"Directory is not readable: {path}")
    return _check(name, "pass", f"Directory is readable: {path}")


def _database_path_from_url(database_url: str) -> Optional[Path]:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None

    raw_path = database_url[len(prefix):]
    if not raw_path or raw_path == ":memory:":
        return None
    return Path(raw_path).expanduser().resolve()


def _check_database_url(database_url: str, database_file: Path) -> Dict[str, str]:
    try:
        backend = make_url(database_url).get_backend_name()
    except ArgumentError:
        return _check(
            "database_url",
            "fail",
            "POLARIS_DATABASE_URL is not a valid database URL.",
        )

    if backend == "postgresql":
        return _check(
            "database_url",
            "pass",
            "POLARIS_DATABASE_URL selects PostgreSQL.",
        )
    if backend != "sqlite":
        return _check(
            "database_url",
            "fail",
            "Polaris supports only SQLite or PostgreSQL database URLs.",
        )

    configured_path = _database_path_from_url(database_url)
    expected_path = database_file.expanduser().resolve()
    if configured_path is None:
        return _check(
            "database_url",
            "fail",
            "DATABASE_URL must identify a file-backed SQLite database.",
        )
    if configured_path != expected_path:
        return _check(
            "database_url",
            "fail",
            (
                "DATABASE_URL does not match DATABASE_FILE: "
                f"{configured_path} != {expected_path}"
            ),
        )
    return _check(
        "database_url",
        "pass",
        f"DATABASE_URL resolves to {expected_path}",
    )


def required_database_tables(environment: str) -> set:
    required_tables = set(LOCAL_REQUIRED_DATABASE_TABLES)
    if environment in {"production", "staging"}:
        required_tables.update(HOSTED_REQUIRED_DATABASE_TABLES)
    return required_tables


def _check_sqlite_database(
    database_file: Path,
    required_tables: set,
) -> Dict[str, str]:
    resolved_path = database_file.expanduser().resolve()
    if not resolved_path.is_file():
        return _check(
            "database",
            "fail",
            f"Database file was not found: {resolved_path}",
        )
    if not os.access(resolved_path, os.R_OK):
        return _check(
            "database",
            "fail",
            f"Database file is not readable: {resolved_path}",
        )
    connection = None
    try:
        connection = sqlite3.connect(
            f"{resolved_path.as_uri()}?mode=ro",
            uri=True,
        )
        connection.execute("PRAGMA query_only = ON")
        quick_check = [row[0] for row in connection.execute("PRAGMA quick_check")]
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    except sqlite3.Error as error:
        return _check(
            "database",
            "fail",
            f"Database could not be opened safely: {error}",
        )
    finally:
        if connection is not None:
            connection.close()

    if quick_check != ["ok"]:
        return _check(
            "database",
            "fail",
            f"SQLite quick_check failed: {quick_check}",
        )
    missing_tables = sorted(required_tables - table_names)
    if missing_tables:
        return _check(
            "database",
            "fail",
            f"Database is missing required tables: {', '.join(missing_tables)}",
        )
    return _check(
        "database",
        "pass",
        f"Database is readable, healthy, and has the required schema: {resolved_path}",
    )


def _check_postgresql_database(
    database_url: str,
    required_tables: set,
) -> Dict[str, str]:
    database_engine = None
    try:
        database_engine = create_engine(
            database_url,
            **engine_options(database_url),
        )
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            table_names = set(inspect(connection).get_table_names())
    except (ArgumentError, SQLAlchemyError):
        return _check(
            "database",
            "fail",
            "PostgreSQL is not reachable with the configured credentials.",
        )
    finally:
        if database_engine is not None:
            database_engine.dispose()

    missing_tables = sorted(required_tables - table_names)
    if missing_tables:
        return _check(
            "database",
            "fail",
            "PostgreSQL is missing required tables: "
            f"{', '.join(missing_tables)}",
        )
    return _check(
        "database",
        "pass",
        "PostgreSQL is reachable and has the required schema.",
    )


def _check_database(
    database_url: str,
    database_file: Path,
    required_tables: set,
) -> Dict[str, str]:
    try:
        backend = make_url(database_url).get_backend_name()
    except ArgumentError:
        return _check(
            "database",
            "fail",
            "Database health cannot be checked until the URL is valid.",
        )
    if backend == "sqlite":
        return _check_sqlite_database(database_file, required_tables)
    if backend == "postgresql":
        return _check_postgresql_database(database_url, required_tables)
    return _check(
        "database",
        "fail",
        "Database health cannot be checked for an unsupported backend.",
    )


def _check_web_assets(web_directory: Path) -> Dict[str, str]:
    directory_check = _check_directory("web_assets", web_directory)
    if directory_check["status"] == "fail":
        return directory_check

    missing_assets = sorted(
        filename
        for filename in REQUIRED_WEB_ASSETS
        if not (web_directory / filename).is_file()
        or not os.access(web_directory / filename, os.R_OK)
    )
    if missing_assets:
        return _check(
            "web_assets",
            "fail",
            f"Required operator assets are missing: {', '.join(missing_assets)}",
        )
    return _check(
        "web_assets",
        "pass",
        f"All required operator assets are readable: {web_directory}",
    )


def run_startup_preflight(
    base_dir: Path = settings.BASE_DIR,
    database_file: Path = settings.DATABASE_FILE,
    database_url: str = settings.DATABASE_URL,
    library_root: Path = POLARIS_ROOT,
    log_level: str = settings.LOG_LEVEL,
    require_local_capture_library: bool = (
        settings.REQUIRE_LOCAL_CAPTURE_LIBRARY
    ),
    environment: str = settings.ENVIRONMENT,
    web_directory: Optional[Path] = None,
) -> Dict:
    resolved_base = base_dir.expanduser().resolve()
    resolved_database = database_file.expanduser().resolve()
    resolved_library = library_root.expanduser().resolve()
    resolved_web = (
        web_directory.expanduser().resolve()
        if web_directory is not None
        else resolved_base / "app" / "web"
    )
    normalized_log_level = log_level.upper().strip()
    required_tables = required_database_tables(environment)
    checks: List[Dict[str, str]] = [
        _check_directory("application_root", resolved_base),
        _check_web_assets(resolved_web),
        _check_database_url(database_url, resolved_database),
        _check_database(
            database_url,
            resolved_database,
            required_tables,
        ),
    ]
    if require_local_capture_library:
        checks.extend(
            [
                _check_directory(
                    "capture_library",
                    resolved_library,
                ),
                _check_directory(
                    "capture_targets",
                    resolved_library / "targets",
                ),
            ]
        )
    if normalized_log_level in VALID_LOG_LEVELS:
        checks.append(
            _check(
                "log_level",
                "pass",
                f"Log level is valid: {normalized_log_level}",
            )
        )
    else:
        checks.append(
            _check(
                "log_level",
                "fail",
                (
                    f"Unsupported POLARIS_LOG_LEVEL '{log_level}'. "
                    f"Choose one of: {', '.join(sorted(VALID_LOG_LEVELS))}."
                ),
            )
        )

    failures = [check for check in checks if check["status"] == "fail"]
    return {
        "ready": not failures,
        "status": "Ready" if not failures else "Blocked",
        "check_count": len(checks),
        "failure_count": len(failures),
        "checks": checks,
        "failures": failures,
    }


def format_preflight_failure(report: Dict) -> str:
    lines = ["Project Polaris startup preflight failed:"]
    lines.extend(
        f"- {failure['name']}: {failure['message']}"
        for failure in report.get("failures", [])
    )
    return "\n".join(lines)


def log_preflight_report(report: Dict, logger: logging.Logger) -> None:
    for check in report["checks"]:
        log_method = logger.info if check["status"] == "pass" else logger.error
        log_method(
            "startup_preflight check=%s status=%s message=%s",
            check["name"],
            check["status"],
            check["message"],
        )
