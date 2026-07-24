import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text


def test_migrations_build_clean_database(tmp_path: Path):
    database_path = tmp_path / "polaris-migration-test.db"
    database_url = f"sqlite:///{database_path}"
    environment = os.environ.copy()
    environment["POLARIS_DATABASE_URL"] = database_url
    environment["POLARIS_ENVIRONMENT"] = "test"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    migration_check = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "check",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert migration_check.returncode == 0, migration_check.stderr

    engine = create_engine(database_url)
    with engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    engine.dispose()

    assert table_names == {
        "alembic_version",
        "candidate_sites",
        "capture_analyses",
        "captures",
        "observatories",
        "profiles",
        "recommendation_feedback",
        "recommendation_runs",
        "sessions",
    }
    assert revision == "20260724_0002"


def test_postgresql_migration_enables_forced_tenant_rls():
    environment = os.environ.copy()
    environment["POLARIS_DATABASE_URL"] = (
        "postgresql+psycopg://user:pass@db.example/polaris"
    )
    environment["POLARIS_ENVIRONMENT"] = "test"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
            "--sql",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    generated_sql = result.stdout.lower()
    for table_name in (
        "profiles",
        "observatories",
        "recommendation_runs",
        "recommendation_feedback",
    ):
        assert (
            f"alter table {table_name} enable row level security"
            in generated_sql
        )
        assert (
            f"alter table {table_name} force row level security"
            in generated_sql
        )
        assert (
            f"create policy {table_name}_owner_isolation"
            in generated_sql
        )
    assert "current_setting('app.current_user_id', true)" in generated_sql
