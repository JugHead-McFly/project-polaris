import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "restore_hosted_tenant_to_postgres.py"
)
SPEC = importlib.util.spec_from_file_location(
    "restore_hosted_tenant_to_postgres",
    SCRIPT_PATH,
)
RESTORE_SCRIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESTORE_SCRIPT)


def test_recovery_target_rejects_source_project():
    with pytest.raises(SystemExit, match="live source project"):
        RESTORE_SCRIPT._validate_target(
            project_ref="abcdefghijklmnopqrst",
            pooler_host="aws-0-us-east-1.pooler.supabase.com",
            source_project_ref="abcdefghijklmnopqrst",
        )


def test_database_url_uses_session_pooler_and_encodes_password():
    database_url = RESTORE_SCRIPT._database_url(
        project_ref="abcdefghijklmnopqrst",
        pooler_host="aws-0-us-east-1.pooler.supabase.com",
        password="example:/?#[]@ password",
    )

    assert database_url.startswith(
        "postgresql+psycopg://postgres.abcdefghijklmnopqrst:"
    )
    assert "example%3A%2F%3F%23%5B%5D%40%20password" in database_url
    assert (
        database_url.endswith(
            "@aws-0-us-east-1.pooler.supabase.com:5432/"
            "postgres?sslmode=require"
        )
    )
