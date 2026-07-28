#!/usr/bin/env python3
"""Restore a verified Polaris tenant export into an empty Supabase project."""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote
from uuid import UUID
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PROJECT_REF_PATTERN = re.compile(r"^[a-z]{20}$")
POOLER_HOST_PATTERN = re.compile(
    r"^aws-[0-9]+-[a-z0-9-]+\.pooler\.supabase\.com$"
)


def _arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Migrate an empty Supabase recovery project and restore one "
            "verified Polaris tenant backup into a recreated Auth user."
        )
    )
    parser.add_argument("backup", type=Path)
    parser.add_argument("--project-ref", required=True)
    parser.add_argument("--pooler-host", required=True)
    parser.add_argument("--target-user-id", type=UUID, required=True)
    parser.add_argument(
        "--source-project-ref",
        help=(
            "Optional live project reference. The command refuses to run "
            "if the recovery target matches it."
        ),
    )
    return parser.parse_args()


def _validate_target(
    *,
    project_ref: str,
    pooler_host: str,
    source_project_ref: str = None,
) -> None:
    if not PROJECT_REF_PATTERN.fullmatch(project_ref):
        raise SystemExit("Recovery project reference is not valid.")
    if not POOLER_HOST_PATTERN.fullmatch(pooler_host):
        raise SystemExit("Recovery pooler host is not valid.")
    if source_project_ref and project_ref == source_project_ref:
        raise SystemExit(
            "Refusing to restore into the live source project."
        )


def _database_url(
    *,
    project_ref: str,
    pooler_host: str,
    password: str,
) -> str:
    username = quote(f"postgres.{project_ref}", safe="")
    encoded_password = quote(password, safe="")
    return (
        f"postgresql+psycopg://{username}:{encoded_password}"
        f"@{pooler_host}:5432/postgres?sslmode=require"
    )


def _activate_runtime_role(database) -> None:
    from sqlalchemy import text

    database.execute(text("SET LOCAL ROLE polaris_app"))


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
    )

    backup_path = arguments.backup.expanduser().resolve()
    with backup_path.open(encoding="utf-8") as backup_file:
        document = json.load(backup_file)

    password = getpass(
        "Recovery-project database password (hidden): "
    )
    if not password:
        raise SystemExit("A database password is required.")

    database_url = _database_url(
        project_ref=project_ref,
        pooler_host=pooler_host,
        password=password,
    )
    del password
    os.environ["POLARIS_DATABASE_URL"] = database_url

    from alembic import command
    from alembic.config import Config
    from sqlalchemy.orm import sessionmaker

    from app.database.database import engine
    from app.database.database import TENANT_SESSION_KEY
    from app.models import HostedObservatory
    from app.models import Profile
    from app.models import RecommendationFeedback
    from app.models import RecommendationRun
    from app.services.hosted_backup_service import restore_hosted_tenant
    from app.services.hosted_backup_service import (
        verify_hosted_tenant_export,
    )

    verification = verify_hosted_tenant_export(document)
    if not verification["valid"]:
        print(json.dumps(verification, indent=2, sort_keys=True))
        raise SystemExit(1)

    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    database_factory = sessionmaker(bind=engine)
    database = database_factory()
    try:
        database.info[TENANT_SESSION_KEY] = arguments.target_user_id
        _activate_runtime_role(database)
        report = restore_hosted_tenant(
            database,
            document=document,
            target_user_id=arguments.target_user_id,
        )

        _activate_runtime_role(database)
        restored_counts = {
            "profiles": database.query(Profile).count(),
            "observatories": database.query(HostedObservatory).count(),
            "recommendation_runs": database.query(
                RecommendationRun
            ).count(),
            "recommendation_feedback": database.query(
                RecommendationFeedback
            ).count(),
        }
    finally:
        database.close()

    if restored_counts != report["counts"]:
        raise SystemExit(
            "Restored database counts did not match the backup manifest."
        )

    isolated_database = database_factory()
    try:
        isolated_database.info[TENANT_SESSION_KEY] = uuid4()
        _activate_runtime_role(isolated_database)
        isolated_counts = {
            "profiles": isolated_database.query(Profile).count(),
            "observatories": isolated_database.query(
                HostedObservatory
            ).count(),
            "recommendation_runs": isolated_database.query(
                RecommendationRun
            ).count(),
            "recommendation_feedback": isolated_database.query(
                RecommendationFeedback
            ).count(),
        }
    finally:
        isolated_database.close()
        engine.dispose()

    if any(isolated_counts.values()):
        raise SystemExit(
            "Row Level Security isolation verification failed."
        )

    print("Recovery restore passed.")
    print(f"Payload SHA-256: {report['payload_sha256']}")
    print(
        "Restored counts: "
        f"{json.dumps(restored_counts, sort_keys=True)}"
    )
    print("Recreated Auth user mapping: passed")
    print("Row Level Security isolation: passed")


if __name__ == "__main__":
    main()
