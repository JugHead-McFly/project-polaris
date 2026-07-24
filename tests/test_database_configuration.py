from app.database.database import engine_options


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
