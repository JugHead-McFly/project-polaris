from unittest.mock import patch
from uuid import UUID

from app.core.auth import CurrentUser
from app.database.database import TENANT_SESSION_KEY
from app.database.database import apply_tenant_context
from app.database.database import engine_options
from app.database.database import get_db
from app.database.database import get_tenant_db


def test_sqlite_engine_keeps_thread_compatibility():
    options = engine_options("sqlite:////tmp/polaris.db")

    assert options["pool_pre_ping"]
    assert options["connect_args"] == {
        "check_same_thread": False,
    }


def test_postgresql_engine_uses_a_bounded_connect_timeout():
    options = engine_options(
        "postgresql+psycopg://user:pass@db.example/polaris"
    )

    assert options == {
        "pool_pre_ping": True,
        "connect_args": {
            "connect_timeout": 10,
        },
    }


class FakeSession:
    def __init__(self):
        self.closed = False
        self.rolled_back = False
        self.info = {}

    def close(self):
        self.closed = True

    def rollback(self):
        self.rolled_back = True


def test_request_database_dependency_closes_session_after_success():
    database = FakeSession()

    with patch(
        "app.database.database.SessionLocal",
        return_value=database,
    ):
        dependency = get_db()
        assert next(dependency) is database
        try:
            next(dependency)
        except StopIteration:
            pass

    assert database.closed
    assert not database.rolled_back


def test_request_database_dependency_rolls_back_on_error():
    database = FakeSession()

    with patch(
        "app.database.database.SessionLocal",
        return_value=database,
    ):
        dependency = get_db()
        next(dependency)
        try:
            dependency.throw(RuntimeError("request failed"))
        except RuntimeError:
            pass

    assert database.closed
    assert database.rolled_back


def test_tenant_database_dependency_carries_authenticated_user():
    database = FakeSession()
    user_id = UUID("9be3ad95-df0f-4672-8aaf-f412e70c880c")
    current_user = CurrentUser(
        user_id=user_id,
        auth_mode="supabase",
    )

    with patch(
        "app.database.database.SessionLocal",
        return_value=database,
    ):
        dependency = get_tenant_db(current_user)
        assert next(dependency) is database
        try:
            next(dependency)
        except StopIteration:
            pass

    assert database.info[TENANT_SESSION_KEY] == user_id
    assert database.closed


class FakeDialect:
    def __init__(self, name):
        self.name = name


class FakeConnection:
    def __init__(self, dialect_name):
        self.dialect = FakeDialect(dialect_name)
        self.executions = []

    def execute(self, statement, parameters):
        self.executions.append((str(statement), parameters))


class FakeTenantSession:
    def __init__(self, user_id):
        self.info = {
            TENANT_SESSION_KEY: user_id,
        }


def test_postgresql_transaction_receives_local_tenant_identity():
    user_id = UUID("9be3ad95-df0f-4672-8aaf-f412e70c880c")
    connection = FakeConnection("postgresql")

    apply_tenant_context(
        FakeTenantSession(user_id),
        transaction=None,
        connection=connection,
    )

    assert len(connection.executions) == 1
    statement, parameters = connection.executions[0]
    assert "set_config" in statement
    assert "'app.current_user_id'" in statement
    assert parameters == {"user_id": str(user_id)}


def test_sqlite_transaction_does_not_set_postgresql_context():
    user_id = UUID("9be3ad95-df0f-4672-8aaf-f412e70c880c")
    connection = FakeConnection("sqlite")

    apply_tenant_context(
        FakeTenantSession(user_id),
        transaction=None,
        connection=connection,
    )

    assert connection.executions == []
