import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_recovery_drill_app.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_recovery_drill_app",
    SCRIPT_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_recovery_viewer_refuses_live_project():
    with pytest.raises(SystemExit, match="live project"):
        MODULE._validate_target(
            project_ref="a" * 20,
            pooler_host="aws-0-us-east-1.pooler.supabase.com",
            source_project_ref="a" * 20,
            port=8002,
        )


def test_runtime_url_uses_restricted_role_and_encodes_password():
    database_url = MODULE._runtime_database_url(
        project_ref="a" * 20,
        pooler_host="aws-0-us-east-1.pooler.supabase.com",
        password="special:/?#[]@ password",
    )

    assert "special%3A%2F%3F%23%5B%5D%40%20password" in database_url
    assert "options=-c%20role%3Dpolaris_app" in database_url
    assert "sslmode=require" in database_url


def test_recovery_viewer_rejects_invalid_port():
    with pytest.raises(SystemExit, match="port"):
        MODULE._validate_target(
            project_ref="a" * 20,
            pooler_host="aws-0-us-east-1.pooler.supabase.com",
            port=80,
        )


def test_configure_environment_disables_monitoring(monkeypatch):
    monkeypatch.delenv("POLARIS_SENTRY_DSN", raising=False)
    monkeypatch.delenv(
        "POLARIS_SENTRY_ALLOW_TRANSMISSION",
        raising=False,
    )

    MODULE._configure_environment(
        project_ref="a" * 20,
        pooler_host="aws-0-us-east-1.pooler.supabase.com",
        password="password",
        publishable_key="sb_publishable_test",
    )

    assert MODULE.os.environ["POLARIS_ENVIRONMENT"] == "staging"
    assert MODULE.os.environ["POLARIS_AUTH_MODE"] == "supabase"
    assert (
        MODULE.os.environ["POLARIS_SUPABASE_URL"]
        == f"https://{'a' * 20}.supabase.co"
    )
    assert (
        MODULE.os.environ["POLARIS_SUPABASE_PUBLISHABLE_KEY"]
        == "sb_publishable_test"
    )
    assert MODULE.os.environ["POLARIS_SENTRY_DSN"] == ""
    assert (
        MODULE.os.environ["POLARIS_SENTRY_ALLOW_TRANSMISSION"]
        == "false"
    )
