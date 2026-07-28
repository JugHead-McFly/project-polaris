#!/usr/bin/env python3
"""Run Polaris locally against a separate Supabase recovery project."""

import argparse
from getpass import getpass
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PROJECT_REF_PATTERN = re.compile(r"^[a-z]{20}$")
POOLER_HOST_PATTERN = re.compile(
    r"^aws-[0-9]+-[a-z0-9-]+\.pooler\.supabase\.com$"
)
PUBLISHABLE_KEY_PATTERN = re.compile(r"^sb_publishable_[A-Za-z0-9_-]+$")


def _arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Start a local Polaris app connected to a separate Supabase "
            "recovery project through the restricted polaris_app role."
        )
    )
    parser.add_argument("--project-ref", required=True)
    parser.add_argument("--pooler-host", required=True)
    parser.add_argument(
        "--source-project-ref",
        help=(
            "Optional live project reference. The command refuses to run "
            "if the recovery target matches it."
        ),
    )
    parser.add_argument("--port", type=int, default=8002)
    return parser.parse_args()


def _validate_target(
    *,
    project_ref: str,
    pooler_host: str,
    source_project_ref: str = None,
    port: int,
) -> None:
    if not PROJECT_REF_PATTERN.fullmatch(project_ref):
        raise SystemExit("Recovery project reference is not valid.")
    if not POOLER_HOST_PATTERN.fullmatch(pooler_host):
        raise SystemExit("Recovery pooler host is not valid.")
    if source_project_ref and project_ref == source_project_ref:
        raise SystemExit(
            "Refusing to run the recovery viewer against the live project."
        )
    if not 1024 <= port <= 65535:
        raise SystemExit("Recovery viewer port must be between 1024 and 65535.")


def _runtime_database_url(
    *,
    project_ref: str,
    pooler_host: str,
    password: str,
) -> str:
    username = quote(f"postgres.{project_ref}", safe="")
    encoded_password = quote(password, safe="")
    runtime_options = quote("-c role=polaris_app", safe="")
    return (
        f"postgresql+psycopg://{username}:{encoded_password}"
        f"@{pooler_host}:5432/postgres"
        f"?sslmode=require&options={runtime_options}"
    )


def _configure_environment(
    *,
    project_ref: str,
    pooler_host: str,
    password: str,
    publishable_key: str,
) -> None:
    os.environ.update(
        {
            "POLARIS_ENVIRONMENT": "staging",
            "POLARIS_AUTH_MODE": "supabase",
            "POLARIS_SUPABASE_URL": (
                f"https://{project_ref}.supabase.co"
            ),
            "POLARIS_SUPABASE_PUBLISHABLE_KEY": publishable_key,
            "POLARIS_SUPABASE_AUDIENCE": "authenticated",
            "POLARIS_DATABASE_URL": _runtime_database_url(
                project_ref=project_ref,
                pooler_host=pooler_host,
                password=password,
            ),
            "POLARIS_REQUIRE_LOCAL_CAPTURE_LIBRARY": "false",
            "POLARIS_SENTRY_DSN": "",
            "POLARIS_SENTRY_ALLOW_TRANSMISSION": "false",
        }
    )


def main() -> None:
    arguments = _arguments()
    project_ref = arguments.project_ref.strip().lower()
    pooler_host = arguments.pooler_host.strip().lower()
    source_project_ref = (
        arguments.source_project_ref.strip().lower()
        if arguments.source_project_ref
        else None
    )
    _validate_target(
        project_ref=project_ref,
        pooler_host=pooler_host,
        source_project_ref=source_project_ref,
        port=arguments.port,
    )

    publishable_key = getpass(
        "Recovery-project publishable key (hidden): "
    ).strip()
    if not PUBLISHABLE_KEY_PATTERN.fullmatch(publishable_key):
        raise SystemExit(
            "The recovery publishable key is not valid."
        )

    password = getpass(
        "Recovery-project database password (hidden): "
    )
    if not password:
        raise SystemExit("A database password is required.")

    _configure_environment(
        project_ref=project_ref,
        pooler_host=pooler_host,
        password=password,
        publishable_key=publishable_key,
    )
    del password
    del publishable_key

    import uvicorn

    print(
        "Recovery viewer starting at "
        f"http://127.0.0.1:{arguments.port}/operator"
    )
    print("Press Control-C when the recovery check is complete.")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=arguments.port,
        workers=1,
    )


if __name__ == "__main__":
    main()
