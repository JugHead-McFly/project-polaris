"""Exercise the actual migration with existing data and PostgreSQL SQL output."""
import importlib.util
from io import StringIO
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def migration():
    path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261013_0012_legacy_capture_history.py'
    spec = importlib.util.spec_from_file_location('legacy_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_and_downgrade_preserve_existing_history():
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE profiles (user_id CHAR(32) PRIMARY KEY)')
        conn.exec_driver_sql('CREATE TABLE capture_history (id INTEGER PRIMARY KEY, integration_seconds FLOAT)')
        conn.exec_driver_sql('INSERT INTO capture_history VALUES (1,34800)')
        module = migration()
        module.op = Operations(MigrationContext.configure(conn))
        module.upgrade()
        assert 'legacy_capture_history' in inspect(conn).get_table_names()
        assert conn.exec_driver_sql('SELECT * FROM capture_history').all() == [(1,34800)]
        constraints = inspect(conn).get_unique_constraints('legacy_capture_history')
        assert any(c['column_names'] == ['user_id','source_key'] for c in constraints)
        module.downgrade()
        assert 'legacy_capture_history' not in inspect(conn).get_table_names()
        assert conn.exec_driver_sql('SELECT * FROM capture_history').all() == [(1,34800)]
    engine.dispose()


def test_postgresql_migration_emits_owner_policy_and_restricted_grants():
    output = StringIO()
    module = migration()
    module.op = Operations(MigrationContext.configure(dialect_name='postgresql',
        opts={'as_sql':True,'output_buffer':output}))
    module.upgrade()
    sql = output.getvalue()
    assert 'ENABLE ROW LEVEL SECURITY' in sql
    assert 'FORCE ROW LEVEL SECURITY' in sql
    assert "current_setting('app.current_user_id', true)" in sql
    assert 'WITH CHECK' in sql
    assert 'FROM PUBLIC, anon, authenticated' in sql
    assert 'TO polaris_app' in sql
