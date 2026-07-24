import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text


def test_baseline_migration_builds_clean_database(tmp_path: Path):
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
        "sessions",
    }
    assert revision == "20260724_0001"
