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
        observatory_columns = {
            column["name"]
            for column in inspect(connection).get_columns("observatories")
        }
        forecast_columns = {
            column["name"]: column
            for column in inspect(connection).get_columns(
                "forecast_accuracy_snapshots"
            )
        }
        forecast_unique_constraints = {
            constraint["name"]: set(constraint["column_names"])
            for constraint in inspect(connection).get_unique_constraints(
                "forecast_accuracy_snapshots"
            )
        }
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
        "forecast_accuracy_snapshots",
        "sessions",
    }
    assert "rig_profile_key" in observatory_columns
    assert "forecast_lead_hour" in forecast_columns
    assert forecast_columns["forecast_lead_hour"]["default"] is not None
    assert forecast_unique_constraints[
        "uq_forecast_accuracy_observatory_hour_lead"
    ] == {
        "observatory_id",
        "user_id",
        "forecast_for",
        "forecast_lead_hour",
    }
    assert revision == "20260901_0008"


def test_forecast_horizon_migration_backfills_existing_snapshot(tmp_path: Path):
    database_path = tmp_path / "polaris-horizon-migration.db"
    database_url = f"sqlite:///{database_path}"
    environment = os.environ.copy()
    environment["POLARIS_DATABASE_URL"] = database_url
    environment["POLARIS_ENVIRONMENT"] = "test"
    project_root = Path(__file__).resolve().parents[1]

    before = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "20260830_0007"],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert before.returncode == 0, before.stderr

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO profiles "
                "(user_id, onboarding_state, created_at, updated_at) VALUES "
                "(:user_id, 'complete', :created_at, :created_at)"
            ),
            {
                "user_id": "11111111111141118111111111111111",
                "created_at": "2026-08-30 18:00:00",
            },
        )
        connection.execute(
            text(
                "INSERT INTO observatories "
                "(id, user_id, name, latitude, longitude, "
                "coordinates_are_approximate, timezone_name, created_at, "
                "updated_at) VALUES (:id, :user_id, 'Home', 33.3, -111.7, "
                "1, 'America/Phoenix', :created_at, :created_at)"
            ),
            {
                "id": "aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaaa",
                "user_id": "11111111111141118111111111111111",
                "created_at": "2026-08-30 18:00:00",
            },
        )
        connection.execute(
            text(
                "INSERT INTO forecast_accuracy_snapshots "
                "(id, user_id, observatory_id, forecast_for, "
                "forecast_created_at, status, expires_at, created_at, "
                "updated_at) VALUES (:id, :user_id, :observatory_id, "
                ":forecast_for, :forecast_created_at, 'matched', "
                ":expires_at, :created_at, :created_at)"
            ),
            {
                "id": "dddddddddddd4ddd8ddddddddddddddd",
                "user_id": "11111111111141118111111111111111",
                "observatory_id": "aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaaa",
                "forecast_for": "2026-08-31 03:00:00",
                "forecast_created_at": "2026-08-30 18:00:00",
                "expires_at": "2026-08-31 05:00:00",
                "created_at": "2026-08-30 18:00:00",
            },
        )
    engine.dispose()

    after = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert after.returncode == 0, after.stderr

    engine = create_engine(database_url)
    with engine.connect() as connection:
        lead_hour = connection.execute(
            text(
                "SELECT forecast_lead_hour "
                "FROM forecast_accuracy_snapshots"
            )
        ).scalar_one()
    engine.dispose()

    assert lead_hour == 9


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
    assert (
        "alter table alembic_version enable row level security"
        in generated_sql
    )
    assert (
        "alter table alembic_version force row level security"
        not in generated_sql
    )
    for table_name in (
        "sessions",
        "candidate_sites",
        "captures",
        "capture_analyses",
        "profiles",
        "observatories",
        "recommendation_runs",
        "recommendation_feedback",
        "forecast_accuracy_snapshots",
    ):
        assert (
            f"alter table {table_name} enable row level security"
            in generated_sql
        )
        assert (
            f"alter table {table_name} force row level security"
            in generated_sql
        )
    for table_name in (
        "profiles",
        "observatories",
        "recommendation_runs",
        "recommendation_feedback",
        "forecast_accuracy_snapshots",
    ):
        assert (
            f"create policy {table_name}_owner_isolation"
            in generated_sql
        )
    assert "current_setting('app.current_user_id', true)" in generated_sql
    assert "forecast_accuracy_snapshots_owner_isolation" in generated_sql
    assert (
        "alter table forecast_accuracy_snapshots no force row level security"
        in generated_sql
    )
    assert "create role polaris_app" in generated_sql
    assert "nobypassrls" in generated_sql
    assert (
        "grant select, insert, update, delete "
        "on table profiles, observatories, recommendation_runs, "
        "recommendation_feedback to polaris_app"
        in " ".join(generated_sql.split())
    )
    assert "from authenticated" in generated_sql
    assert "'grant polaris_app to %i'" in generated_sql


def test_tenant_rehearsal_checks_forecast_history_isolation():
    rehearsal = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "verify_postgresql_tenant_isolation.sql"
    ).read_text(encoding="utf-8").lower()

    assert "insert into forecast_accuracy_snapshots" in rehearsal
    assert "forecast_lead_hour" in rehearsal
    assert "bob directly read alice forecast history" in rehearsal
    assert "bob updated alice forecast history" in rehearsal
    assert "bob deleted alice forecast history" in rehearsal
    assert "missing identity exposed % forecast history rows" in rehearsal
