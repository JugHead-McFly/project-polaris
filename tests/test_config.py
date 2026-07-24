from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.config import normalize_database_url


def test_local_settings_preserve_existing_database_default(tmp_path: Path):
    configured = Settings(base_dir=tmp_path)

    assert configured.ENVIRONMENT == "local"
    assert configured.DATABASE_FILE == tmp_path / "polaris.db"
    assert configured.DATABASE_URL == f"sqlite:///{tmp_path / 'polaris.db'}"
    assert configured.REQUIRE_LOCAL_CAPTURE_LIBRARY


@pytest.mark.parametrize(
    ("provided", "expected"),
    [
        (
            "postgres://user:pass@db.example/polaris",
            "postgresql+psycopg://user:pass@db.example/polaris",
        ),
        (
            "postgresql://user:pass@db.example/polaris",
            "postgresql+psycopg://user:pass@db.example/polaris",
        ),
        (
            "postgresql+psycopg://user:pass@db.example/polaris",
            "postgresql+psycopg://user:pass@db.example/polaris",
        ),
    ],
)
def test_postgresql_urls_select_psycopg_3(provided, expected):
    assert normalize_database_url(provided) == expected


def test_hosted_environment_rejects_sqlite(tmp_path: Path):
    with pytest.raises(ValueError, match="require PostgreSQL"):
        Settings(
            environment="production",
            base_dir=tmp_path,
        )


def test_hosted_environment_does_not_require_local_archive():
    configured = Settings(
        environment="staging",
        database_url="postgresql://user:pass@db.example/polaris",
    )

    assert not configured.REQUIRE_LOCAL_CAPTURE_LIBRARY
