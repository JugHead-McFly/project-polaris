from unittest.mock import patch

from app.database.database import engine_options
from app.database.database import get_db


def test_sqlite_engine_keeps_thread_compatibility():
    options = engine_options("sqlite:////tmp/polaris.db")

    assert options["pool_pre_ping"]
    assert options["connect_args"] == {
        "check_same_thread": False,
    }


def test_postgresql_engine_does_not_receive_sqlite_options():
    options = engine_options(
        "postgresql+psycopg://user:pass@db.example/polaris"
    )

    assert options == {
        "pool_pre_ping": True,
    }


class FakeSession:
    def __init__(self):
        self.closed = False
        self.rolled_back = False

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
